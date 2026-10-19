#!/usr/bin/env python3
"""Capture a 60-message E00 run from the physical ESP32 firmware."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from labcompose import compose as compose_argv


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def command(argv: list[str], env: dict[str, str], *, timeout: int = 120,
            check: bool = True) -> str:
    result = subprocess.run(argv, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(argv)}\n{result.stdout[-4000:]}")
    return result.stdout


def event_count(path: Path, event: str) -> int:
    if not path.exists():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            count += json.loads(line).get("event") == event
        except json.JSONDecodeError:
            continue
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture 60 telemetry messages from ESP32 firmware")
    parser.add_argument("--run-id", default=None, help="Unique ID using letters, digits, underscore or hyphen")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Seconds to wait for 60 ESP32 messages (default: 120)")
    args = parser.parse_args()
    if args.timeout < 10:
        parser.error("--timeout must be at least 10 seconds")
    run_id = args.run_id or f"E00-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{secrets.token_hex(2)}"
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        parser.error("run_id may contain only letters, digits, underscore and hyphen")
    for required_file in (ROOT / ".env", ROOT / ".env.firmware",
                          ROOT / "config/mosquitto/auth/passwords"):
        if not required_file.is_file():
            parser.error(f"Missing {required_file.name}; configure the lab and firmware first")

    env = os.environ.copy()
    env.update(RUN_ID=run_id)
    project = f"mqtt-lab-{run_id.lower().replace('_', '-')}"
    compose = compose_argv("compose.yaml", "compose.firmware.yaml",
                           env_files=(".env", ".env.firmware"), project=project)
    command(["docker", "version"], env, timeout=15)
    command(compose + ["config", "--quiet"], env, timeout=15)

    folder = RAW_DIR / run_id
    folder.mkdir(parents=True, exist_ok=False)
    folder.chmod(0o777)  # clients run as uid 1000
    manifest = {
        "run_id": run_id, "scenario_id": "E00", "label": "esp32-firmware-baseline",
        "mqtt_version": "3.1.1", "transport": "plaintext", "source": "ESP32 DevKit firmware",
        "expected_messages": 60, "qos": 1, "started_at_utc": None, "ended_at_utc": None,
        "status": "started",
        "artifacts": ["baseline.pcap", "broker.log", "capture.log", "subscriber.log",
                      "subscriber.jsonl", "manifest.json"],
    }
    error = None
    print(f"Run {run_id}: building observer/capture images and starting firmware broker", flush=True)
    try:
        command(compose + ["build", "subscriber", "test_client", "capture"], env, timeout=600)
        command(compose + ["up", "-d", "broker", "broker_tls"], env)
        for attempt in range(10):
            try:
                probe = command(compose + ["run", "--rm", "test_client"], env, timeout=30)
                if "PROBE_OK" not in probe:
                    raise RuntimeError(f"Test client probe failed: {probe[-1000:]}")
                break
            except RuntimeError:
                if attempt == 9:
                    raise
                time.sleep(1)
        command(compose + ["up", "-d", "capture", "subscriber"], env)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            logs = command(compose + ["logs", "--no-color", "capture", "subscriber"], env, check=False)
            if "listening on eth0" in logs and "SUBSCRIBED" in logs:
                break
            time.sleep(0.5)
        else:
            raise TimeoutError(f"Capture/subscriber did not become ready:\n{logs[-2000:]}")
        manifest["started_at_utc"] = now_utc()
        print("Capture ready. Reset or power on the ESP32 now; waiting for 60 QoS 1 telemetry messages.", flush=True)
        deadline = time.monotonic() + args.timeout
        while event_count(folder / "subscriber.jsonl", "message") < 60 and time.monotonic() < deadline:
            time.sleep(0.5)
        received = event_count(folder / "subscriber.jsonl", "message")
        if received < 60:
            raise TimeoutError(f"Received {received}/60 ESP32 telemetry messages within {args.timeout}s")
        manifest["traffic_ended_at_utc"] = now_utc()
        print("Received 60 telemetry messages; collecting PCAP and logs", flush=True)
    except (RuntimeError, subprocess.TimeoutExpired, TimeoutError) as exc:
        error = str(exc)
        print(f"Run failed: {error}", file=sys.stderr, flush=True)
    finally:
        command(compose + ["stop", "-t", "10", "subscriber", "capture"], env, timeout=40, check=False)
        manifest["ended_at_utc"] = now_utc()
        for service in ("broker", "capture", "subscriber"):
            (folder / f"{service}.log").write_text(
                command(compose + ["logs", "--no-color", "--timestamps", service], env, check=False),
                encoding="utf-8",
            )
        manifest["actual_receives"] = event_count(folder / "subscriber.jsonl", "message")
        pcap = folder / "baseline.pcap"
        manifest["pcap_bytes"] = pcap.stat().st_size if pcap.exists() else 0
        manifest["broker_image_id"] = command(
            ["docker", "image", "inspect", "eclipse-mosquitto:2.1.2-alpine", "--format", "{{.Id}}"],
            env, check=False).strip()
        if error is None and (manifest["actual_receives"] < 60 or manifest["pcap_bytes"] <= 24):
            error = "Expected 60 received messages and a non-empty PCAP"
        manifest["status"] = "complete" if error is None else "failed"
        if error:
            manifest["error"] = error
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        command(compose + ["down", "-v"], env, timeout=60, check=False)
    print(f"Artifacts: {folder}", flush=True)
    return 0 if error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
