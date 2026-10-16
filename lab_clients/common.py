"""Shared helpers for bounded, synthetic MQTT traffic."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt


TOPIC = "factory/line-01/machine-01/telemetry"
STATUS_TOPIC = "factory/line-01/machine-01/status"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


class EventWriter:
    def __init__(self, filename: str):
        run_id = required("RUN_ID")
        folder = Path("/artifacts") / run_id
        folder.mkdir(parents=True, exist_ok=True)
        self._file = (folder / filename).open("a", encoding="utf-8")
        self._lock = threading.Lock()

    def write(self, event: str, **fields: object) -> None:
        record = {"timestamp_utc": utc_now(), "event": event, **fields}
        with self._lock:
            self._file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            self._file.flush()

    def close(self) -> None:
        self._file.close()


def make_client(client_id: str, username_key: str, password_key: str) -> mqtt.Client:
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
        clean_session=True,
        protocol=mqtt.MQTTv311,
    )
    client.username_pw_set(required(username_key), required(password_key))
    return client


def connect_and_wait(client: mqtt.Client, ready: threading.Event, errors: list[str], timeout: float = 15) -> None:
    client.connect(os.environ.get("MQTT_HOST", "broker"), int(os.environ.get("MQTT_PORT", "1883")), 30)
    client.loop_start()
    if not ready.wait(timeout):
        raise TimeoutError("Timed out waiting for MQTT CONNACK")
    if errors:
        raise RuntimeError(errors[0])


def disconnect(client: mqtt.Client) -> None:
    client.disconnect()
    client.loop_stop()
