#!/usr/bin/env python3
"""Create synthetic credentials and a Mosquitto password file for this lab."""

from __future__ import annotations

import argparse
import ipaddress
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
TLS_DIR = AUTH_DIR / "tls"
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


def openssl(*args: str) -> str:
    result = subprocess.run(["openssl", *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"openssl {args[0]} failed: {result.stderr[-500:]}")
    return result.stdout


def firmware_host() -> str:
    path = ROOT / ".env.firmware"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "MQTT_HOST" and value.strip():
                return value.strip().strip("'\"")
    return ""


def ensure_tls() -> None:
    """Create the lab CA once, and a server cert whose SAN covers the firmware's MQTT_HOST."""
    TLS_DIR.mkdir(parents=True, exist_ok=True)
    ca_key, ca_crt = TLS_DIR / "ca.key", TLS_DIR / "ca.crt"
    server_key, server_crt = TLS_DIR / "server.key", TLS_DIR / "server.crt"
    if not (ca_key.exists() and ca_crt.exists()):
        openssl("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "3650",
                "-keyout", str(ca_key), "-out", str(ca_crt), "-subj", "/CN=mqtt-lab-ca",
                "-addext", "basicConstraints=critical,CA:TRUE",
                "-addext", "keyUsage=critical,keyCertSign,cRLSign")
        ca_key.chmod(0o600)
        print("Created lab CA in config/mosquitto/auth/tls/")
    host = firmware_host()
    try:
        ipaddress.ip_address(host)
        names = [f"IP:{host}", f"DNS:{host}"]  # old mbedtls on ESP32 may only match dNSName/CN
    except ValueError:
        names = [f"DNS:{host}"] if host else []
    names += ["DNS:localhost", "DNS:broker", "IP:127.0.0.1"]
    if server_crt.exists() and server_key.exists():
        san = openssl("x509", "-in", str(server_crt), "-noout", "-ext", "subjectAltName").splitlines()[-1]
        if set(names) <= {item.strip().replace("IP Address:", "IP:") for item in san.split(",")}:
            return
    csr, ext = TLS_DIR / "server.csr", TLS_DIR / "server.ext"
    server_key.unlink(missing_ok=True)
    ext.write_text("subjectAltName=" + ",".join(names) + "\nextendedKeyUsage=serverAuth\n", encoding="utf-8")
    try:
        openssl("req", "-newkey", "rsa:2048", "-nodes", "-keyout", str(server_key), "-out", str(csr),
                "-subj", f"/CN={host or 'broker'}")
        openssl("x509", "-req", "-in", str(csr), "-CA", str(ca_crt), "-CAkey", str(ca_key),
                "-CAcreateserial", "-out", str(server_crt), "-days", "3650", "-extfile", str(ext))
    finally:
        csr.unlink(missing_ok=True)
        ext.unlink(missing_ok=True)
    server_key.chmod(0o600)
    print(f"Issued broker TLS certificate for: {', '.join(names)}")


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
    ensure_tls()
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
               "chown 1883:1883 /auth/passwords /auth/acl.conf /auth/tls/server.key && chmod 600 /auth/passwords /auth/acl.conf /auth/tls/server.key"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"Could not set broker file permissions: {result.stderr[-500:]}")
    print("Installed runtime ACL and restricted both files to Mosquitto uid 1883")


if __name__ == "__main__":
    main()
