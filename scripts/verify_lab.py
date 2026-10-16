#!/usr/bin/env python3
"""Check network isolation, valid auth, invalid auth and ACL denial."""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(argv: list[str], env: dict[str, str], *, check: bool = True, timeout: int = 120) -> str:
    result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f"{' '.join(argv)} failed:\n{(result.stdout + result.stderr)[-2000:]}")
    return result.stdout


def main() -> None:
    if not (ROOT / ".env").is_file() or not (ROOT / "config/mosquitto/auth/passwords").is_file():
        raise RuntimeError("Run python3 scripts/init_lab.py first")
    env = os.environ.copy()
    env.update(RUN_ID=f"VERIFY-{secrets.token_hex(3)}", LOCAL_UID=str(os.getuid()), LOCAL_GID=str(os.getgid()))
    compose = ["docker", "compose", "-p", f"mqtt-lab-{env['RUN_ID'].lower()}"]
    configuration = json.loads(run(compose + ["config", "--format", "json"], env))
    if not configuration["networks"]["lab"]["internal"]:
        raise RuntimeError("Lab network is not internal")
    if configuration["services"]["broker"].get("ports"):
        raise RuntimeError("Broker port is published to the host")
    print("Network is internal; broker has no published port", flush=True)
    try:
        run(compose + ["build", "test_client"], env, timeout=600)
        run(compose + ["up", "-d", "broker"], env)
        for attempt in range(10):
            try:
                output = run(compose + ["run", "--rm", "test_client"], env, timeout=30)
                if "PROBE_OK" not in output:
                    raise RuntimeError("Valid account did not pass")
                break
            except RuntimeError:
                if attempt == 9:
                    raise
                time.sleep(1)
        print("Valid test account accepted", flush=True)
        for mode, marker in (("anonymous", "EXPECTED_AUTH_REJECTION"),
                             ("wrong-password", "EXPECTED_AUTH_REJECTION"),
                             ("acl-deny", "ACL_TEST_PUBLISH_SENT")):
            output = run(compose + ["run", "--rm", "test_client", "python", "-m",
                                    "lab_clients.test_client", mode], env, timeout=30)
            if marker not in output:
                raise RuntimeError(f"{mode} did not produce {marker}: {output[-1000:]}")
            print(f"{mode}: {marker}", flush=True)
        logs = run(compose + ["logs", "--no-color", "broker"], env)
        denial = f"Denied PUBLISH from test-{env['RUN_ID']}-acl-deny"
        if denial not in logs:
            raise RuntimeError("Broker did not log the expected ACL-denied PUBLISH")
        print("Broker confirmed ACL-denied PUBLISH", flush=True)
        output = run(compose + ["run", "--rm", "test_client", "python", "-m",
                                "lab_clients.test_client", "monitor-probe"], env, timeout=40)
        if "MONITOR_READ_OK telemetry_and_sys" not in output:
            raise RuntimeError(f"Monitor did not read telemetry and $SYS: {output[-1000:]}")
        logs = run(compose + ["logs", "--no-color", "broker"], env)
        monitor_denial = f"Denied PUBLISH from monitor-{env['RUN_ID']}-monitor-probe"
        if monitor_denial not in logs:
            raise RuntimeError("Broker did not log the monitor's ACL-denied PUBLISH")
        print("Monitor read telemetry and $SYS; its PUBLISH was denied", flush=True)
    finally:
        run(compose + ["down", "-v"], env, check=False, timeout=60)


if __name__ == "__main__":
    main()
