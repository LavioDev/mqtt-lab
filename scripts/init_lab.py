#!/usr/bin/env python3
"""Create synthetic credentials and a Mosquitto password file for this lab."""

from __future__ import annotations

import argparse
import os
import re
import secrets
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
AUTH_DIR = ROOT / "config" / "mosquitto" / "auth"
PASSWORD_FILE = AUTH_DIR / "passwords"
ACL_FILE = AUTH_DIR / "acl.conf"
USERS = ("SENSOR", "SUBSCRIBER", "TEST_CLIENT", "MONITOR")


def ensure_monitor_credentials() -> None:
    if not ENV_FILE.exists():
        return
    content = ENV_FILE.read_text(encoding="utf-8")
    values = {}
    for line in content.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            values[key.strip()] = value.strip()
    additions = []
    for key, value in (("MONITOR_USERNAME", "monitor"),
                       ("MONITOR_PASSWORD", secrets.token_urlsafe(24))):
        if not values.get(key):
            additions.append(f"{key}={value}")
    if additions:
        with ENV_FILE.open("a", encoding="utf-8") as handle:
            handle.write("\n# Read-only MQTT account used by the local dashboard\n")
            handle.write("\n".join(additions) + "\n")
        ENV_FILE.chmod(0o600)


def read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not key or not value:
            raise ValueError(f"Invalid .env line: {line!r}")
        values[key] = value
    for role in USERS:
        if not values.get(f"{role}_USERNAME") or not values.get(f"{role}_PASSWORD"):
            raise ValueError(f"Missing {role} credentials in .env")
        if values[f"{role}_PASSWORD"].startswith("replace-"):
            raise ValueError("Replace placeholder passwords in .env or remove it to generate credentials")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", values["MONITOR_USERNAME"]):
        raise ValueError("MONITOR_USERNAME may contain only letters, digits, underscore, dot and hyphen")
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare synthetic lab credentials")
    parser.add_argument("--credentials-only", action="store_true",
                        help="Create .env without Docker; hash passwords on a later run")
    args = parser.parse_args()
    if not ENV_FILE.exists():
        lines = ["# Synthetic, local-only MQTT lab credentials"]
        for role in USERS:
            lines.append(f"{role}_USERNAME={role.lower()}")
            lines.append(f"{role}_PASSWORD={secrets.token_urlsafe(24)}")
        ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        ENV_FILE.chmod(0o600)
    ensure_monitor_credentials()
    if ENV_FILE.exists():
        ENV_FILE.chmod(0o600)
    values = read_env()
    if args.credentials_only:
        print("Credential file ready; run again without --credentials-only when Docker is available")
        return
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    temporary = AUTH_DIR / "passwords.tmp"
    temporary.unlink(missing_ok=True)
    try:
        if PASSWORD_FILE.exists():
            copy_command = [
                "docker", "run", "--rm", "-v", f"{AUTH_DIR}:/auth", "--entrypoint", "sh",
                "eclipse-mosquitto:2.1.2-alpine", "-c",
                f"cp /auth/passwords /auth/passwords.tmp && chown {os.getuid()}:{os.getgid()} /auth/passwords.tmp && chmod 600 /auth/passwords.tmp",
            ]
            copied = subprocess.run(copy_command, cwd=ROOT, capture_output=True, text=True)
            if copied.returncode:
                raise RuntimeError(f"Could not copy protected password file: {copied.stderr[-500:]}")
        else:
            temporary.touch()
        for index, role in enumerate(USERS):
            command = [
                "docker", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}",
                "-v", f"{AUTH_DIR}:/auth", "--entrypoint", "mosquitto_passwd",
                "eclipse-mosquitto:2.1.2-alpine",
            ]
            if index == 0 and not PASSWORD_FILE.exists():
                command.append("-c")
            command.extend(["-b", "/auth/passwords.tmp", values[f"{role}_USERNAME"], values[f"{role}_PASSWORD"]])
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(f"mosquitto_passwd failed for {role}: {result.stderr[-500:]}")
        temporary.replace(PASSWORD_FILE)
    finally:
        temporary.unlink(missing_ok=True)
    print("Synchronized hashed Mosquitto credentials from .env")

    temporary_acl = AUTH_DIR / "acl.tmp"
    acl_template = (ROOT / "config/mosquitto/acl.conf").read_text(encoding="utf-8")
    temporary_acl.write_text(acl_template.replace("@MONITOR_USERNAME@", values["MONITOR_USERNAME"]), encoding="utf-8")
    temporary_acl.replace(ACL_FILE)
    command = ["docker", "run", "--rm", "-v", f"{AUTH_DIR}:/auth", "--entrypoint", "sh",
               "eclipse-mosquitto:2.1.2-alpine", "-c",
               "chown 1883:1883 /auth/passwords /auth/acl.conf && chmod 600 /auth/passwords /auth/acl.conf"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"Could not set broker file permissions: {result.stderr[-500:]}")
    print("Installed runtime ACL and restricted both files to Mosquitto uid 1883")


if __name__ == "__main__":
    main()
