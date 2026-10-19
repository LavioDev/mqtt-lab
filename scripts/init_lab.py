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
CERT_DIR = ROOT / "config" / "mosquitto" / "certs"  # mounted into the broker: public certs + server key only
PKI_DIR = ROOT / "data" / "pki"  # CA private key stays out of the broker mount
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


def firmware_hosts() -> list[str]:
    """Names/IPs the ESP32 may use to reach the broker; they go into the server cert SAN."""
    hosts: list[str] = []
    firmware_env = ROOT / ".env.firmware"
    if firmware_env.is_file():
        for line in firmware_env.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() in {"MQTT_HOST", "BROKER_BIND_IP"} and value.strip():
                hosts.append(value.strip().strip("'\""))
    return hosts


def san_entry(host: str) -> str:
    return f"IP:{host}" if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host) else f"DNS:{host}"


def openssl(*args: str) -> None:
    result = subprocess.run(["openssl", *args], cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"openssl {args[0]} failed: {result.stderr[-500:]}")


def ensure_tls() -> None:
    """Create a lab CA and a broker server certificate for the 8883 listener (idempotent)."""
    PKI_DIR.mkdir(parents=True, exist_ok=True)
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    ca_key, ca_crt = PKI_DIR / "ca.key", CERT_DIR / "ca.crt"
    key_args = ["-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1", "-nodes"]
    if not (ca_key.is_file() and ca_crt.is_file()):
        openssl("req", "-x509", *key_args, "-keyout", str(ca_key), "-out", str(ca_crt), "-days", "3650",
                "-subj", "/CN=mqtt-lab CA", "-addext", "basicConstraints=critical,CA:TRUE",
                "-addext", "keyUsage=critical,keyCertSign,cRLSign")
        ca_key.chmod(0o600)
        print("Created lab CA (data/pki/ca.key, config/mosquitto/certs/ca.crt)")
        (CERT_DIR / "server.crt").unlink(missing_ok=True)  # old server cert no longer matches this CA
    san = ",".join(dict.fromkeys(["DNS:broker", "DNS:broker_tls", "DNS:localhost", "IP:127.0.0.1",
                                  *(san_entry(host) for host in firmware_hosts())]))
    server_crt, server_key, san_file = CERT_DIR / "server.crt", CERT_DIR / "server.key", CERT_DIR / "server.san"
    if not (server_crt.is_file() and server_key.is_file()
            and san_file.is_file() and san_file.read_text(encoding="utf-8") == san):
        csr, ext = PKI_DIR / "server.csr", PKI_DIR / "server.ext"
        openssl("req", "-new", *key_args, "-keyout", str(server_key), "-out", str(csr), "-subj", "/CN=broker")
        ext.write_text(f"subjectAltName={san}\nbasicConstraints=CA:FALSE\nextendedKeyUsage=serverAuth\n",
                       encoding="utf-8")
        openssl("x509", "-req", "-in", str(csr), "-CA", str(ca_crt), "-CAkey", str(ca_key),
                "-CAcreateserial", "-out", str(server_crt), "-days", "825", "-extfile", str(ext))
        san_file.write_text(san, encoding="utf-8")
        print(f"Issued broker certificate for {san}")
    CERT_DIR.chmod(0o755)
    for path, mode in ((ca_crt, 0o644), (server_crt, 0o644), (san_file, 0o644), (server_key, 0o600)):
        path.chmod(mode)
    os.chown(server_key, 1883, 1883)


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
    # Runs as root inside the tools container: mosquitto_passwd is local, files end up owned by uid 1883.
    PASSWORD_FILE.touch()
    for role in USERS:
        result = subprocess.run(["mosquitto_passwd", "-b", str(PASSWORD_FILE),
                                 values[f"{role}_USERNAME"], values[f"{role}_PASSWORD"]],
                                cwd=ROOT, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f"mosquitto_passwd failed for {role}: {result.stderr[-500:]}")
    print("Synchronized hashed Mosquitto credentials from .env")

    acl_template = (ROOT / "config/mosquitto/acl.conf").read_text(encoding="utf-8")
    ACL_FILE.write_text(acl_template.replace("@MONITOR_USERNAME@", values["MONITOR_USERNAME"]), encoding="utf-8")
    for path in (PASSWORD_FILE, ACL_FILE):
        os.chown(path, 1883, 1883)
        path.chmod(0o600)
    ensure_tls()
    # Client containers run as uid 1000 and write artifacts here.
    (ROOT / "data" / "raw").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "raw").chmod(0o777)
    print("Installed runtime ACL and restricted both files to Mosquitto uid 1883")


if __name__ == "__main__":
    main()
