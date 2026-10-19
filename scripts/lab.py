#!/usr/bin/env python3
"""Docker-only entry point (replaces run.sh); runs inside the tools container."""

from __future__ import annotations

import os
import secrets
import subprocess
import sys
from datetime import datetime, timezone

from labcompose import ROOT, compose

USAGE = "Usage: lab {init|verify|baseline [run-id]|analyze <run-id>|dashboard [stop] [--firmware]|firmware-config}"


def py(script: str, *args: str) -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args], cwd=ROOT, check=True)


def dashboard(args: list[str]) -> None:
    firmware = "--firmware" in args
    stop = "stop" in args
    files, env_files = ["compose.yaml"], (".env",)
    if firmware:
        if not (ROOT / ".env.firmware").is_file():
            raise SystemExit("Missing .env.firmware; fill in ESP32 settings first.")
        files.append("compose.firmware.yaml")
        env_files = (".env", ".env.firmware")
    base = compose(*files, env_files=env_files, profiles=("dashboard",))
    if stop:
        subprocess.run(base + ["stop", "dashboard_proxy", "dashboard"], check=True)
        print("Dashboard stopped. Broker is still running.")
        return
    py("init_lab.py")
    subprocess.run(base + ["config", "--quiet"], check=True)
    subprocess.run(base + ["up", "-d", "--build", "--force-recreate", "broker", "broker_tls", "dashboard", "dashboard_proxy"], check=True)
    print(f"\nDashboard: http://localhost:{os.environ.get('DASHBOARD_PORT', '8081')}")


def main(argv: list[str]) -> int:
    if not argv:
        print(USAGE, file=sys.stderr)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "init":
        py("init_lab.py", *rest)
    elif cmd == "verify":
        py("verify_lab.py")
    elif cmd == "analyze":
        py("analyze_pcap.py", *rest)
    elif cmd == "firmware-config":
        py("generate_firmware_config.py")
    elif cmd == "dashboard":
        dashboard(rest)
    elif cmd == "baseline":
        if not (ROOT / ".env.firmware").is_file():
            raise SystemExit("Missing .env.firmware; fill in ESP32 settings before running the baseline.")
        run_id = rest[0] if rest else f"E00-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{secrets.randbelow(32768)}"
        py("init_lab.py")
        py("verify_lab.py")
        py("run_baseline.py", "--run-id", run_id)
        py("analyze_pcap.py", run_id)
        print(f"\nDone. Artifacts: data/raw/{run_id}")
    else:
        print(USAGE, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode)
