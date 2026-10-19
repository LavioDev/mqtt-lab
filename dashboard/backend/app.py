from __future__ import annotations

import asyncio
import base64
import json
import math
import os
import re
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles


MAX_PAYLOAD_BYTES = 64 * 1024
MAX_MESSAGES = 200
MAX_TELEMETRY_POINTS = 120
MAX_SSE_CLIENTS = 16
FIRMWARE_TOPIC = "factory/line-01/machine-01/telemetry"
SSE_QUEUE_SIZE = 100
STATIC_DIR = Path(__file__).resolve().parent / "static"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class Monitor:
    def __init__(self, name: str, host: str, port: int, tls_ca: str | None = None) -> None:
        self.name, self.host, self.port, self.tls_ca = name, host, port, tls_ca
        self.lock = threading.RLock()
        self.messages: deque[dict[str, Any]] = deque(maxlen=MAX_MESSAGES)
        self.telemetry: deque[dict[str, Any]] = deque(maxlen=MAX_TELEMETRY_POINTS)
        self.metrics: dict[str, int | float] = {}
        self.broker_connected = False
        self.broker_changed_at: str | None = None
        self.broker_stats_at: str | None = None
        self.last_message_at: str | None = None
        self.firmware_messages = 0
        self.firmware_last_seen_at: str | None = None
        self.sequence = 0
        self.telemetry_times: deque[float] = deque()
        self.telemetry_rate = 0.0
        self.loop: asyncio.AbstractEventLoop | None = None
        self.sse_clients: set[asyncio.Queue[dict[str, Any] | None]] = set()
        self.client: mqtt.Client | None = None

    def start(self) -> None:
        self.loop = asyncio.get_running_loop()
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"mqtt-lab-dashboard-{self.name}",
            protocol=mqtt.MQTTv311,
        )
        client.username_pw_set(
            os.environ["MQTT_USERNAME"], os.environ["MQTT_PASSWORD"]
        )
        if self.tls_ca:
            client.tls_set(ca_certs=self.tls_ca)
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        self.client = client
        client.connect_async(
            self.host, self.port, keepalive=30
        )
        client.loop_start()

    def stop(self) -> None:
        if self.client is not None:
            self.client.disconnect()
            self.client.loop_stop()
            self.client = None

    def state(self) -> dict[str, Any]:
        with self.lock:
            return {
                "broker": {
                    "connected": self.broker_connected,
                    "changed_at": self.broker_changed_at,
                    "stats_at": self.broker_stats_at,
                },
                "metrics": dict(self.metrics),
                "telemetry_rate": self.telemetry_rate,
                "last_message_at": self.last_message_at,
                "firmware": {"messages": self.firmware_messages, "last_seen_at": self.firmware_last_seen_at},
                "messages": list(reversed(self.messages)),
                "telemetry": list(self.telemetry),
            }

    def add_sse_client(self) -> asyncio.Queue[dict[str, Any] | None]:
        if len(self.sse_clients) >= MAX_SSE_CLIENTS:
            raise HTTPException(status_code=503, detail="Đã đạt giới hạn kết nối dashboard")
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue(maxsize=SSE_QUEUE_SIZE)
        self.sse_clients.add(queue)
        return queue

    def remove_sse_client(self, queue: asyncio.Queue[dict[str, Any] | None]) -> None:
        self.sse_clients.discard(queue)

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        loop = self.loop
        if loop is None or loop.is_closed():
            return
        event = {"type": event_type, "data": data}
        try:
            loop.call_soon_threadsafe(self._broadcast, event)
        except RuntimeError:
            return

    def _broadcast(self, event: dict[str, Any]) -> None:
        for queue in tuple(self.sse_clients):
            if queue.full():
                while not queue.empty():
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                queue.put_nowait(None)
                self.sse_clients.discard(queue)
            else:
                queue.put_nowait(event)

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        connected = not reason_code.is_failure
        with self.lock:
            self.broker_connected = connected
            self.broker_changed_at = utc_now()
        if connected:
            client.subscribe([("factory/#", 1), ("$SYS/broker/#", 1)])
        self._emit("broker", {"connected": connected, "changed_at": self.broker_changed_at})

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ) -> None:
        with self.lock:
            changed = self.broker_connected
            self.broker_connected = False
            if changed:
                self.broker_changed_at = utc_now()
            changed_at = self.broker_changed_at
        if changed:
            self._emit("broker", {"connected": False, "changed_at": changed_at})

    @staticmethod
    def _decode_payload(payload: bytes) -> dict[str, Any]:
        truncated = len(payload) > MAX_PAYLOAD_BYTES
        raw = payload[:MAX_PAYLOAD_BYTES]
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return {
                "kind": "base64",
                "value": base64.b64encode(raw).decode("ascii"),
                "truncated": truncated,
            }
        kind = "text"
        if not truncated:
            try:
                json.loads(text)
                kind = "json"
            except (json.JSONDecodeError, RecursionError):
                pass
        return {"kind": kind, "value": text, "truncated": truncated}

    @staticmethod
    def _parse_sys_value(topic: str, raw: bytes) -> tuple[str, int | float] | None:
        names = {
            "$SYS/broker/clients/connected": "clients_connected",
            "$SYS/broker/messages/received": "messages_received_total",
            "$SYS/broker/messages/sent": "messages_sent_total",
            "$SYS/broker/bytes/received": "bytes_received_total",
            "$SYS/broker/bytes/sent": "bytes_sent_total",
        }
        name = names.get(topic)
        if name is not None:
            try:
                return name, int(raw.decode("ascii").strip())
            except (ValueError, UnicodeDecodeError):
                return None
        if topic == "$SYS/broker/uptime":
            try:
                text = raw.decode("ascii").strip()
            except UnicodeDecodeError:
                return None
            parts = re.findall(r"(\d+)\s*(days?|d|hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s)", text, re.I)
            if parts:
                seconds = 0
                for amount, unit in parts:
                    unit = unit.lower()
                    scale = 86400 if unit.startswith("d") else 3600 if unit.startswith("h") else 60 if unit.startswith("m") else 1
                    seconds += int(amount) * scale
                return "uptime_seconds", seconds
            if text.isdigit():
                return "uptime_seconds", int(text)
        return None

    def _on_message(self, client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
        if message.topic.startswith("$SYS/"):
            parsed = self._parse_sys_value(message.topic, message.payload)
            if parsed is not None:
                key, value = parsed
                with self.lock:
                    self.metrics[key] = value
                    self.broker_stats_at = utc_now()
                    metrics = dict(self.metrics)
                self._emit("metrics", {"metrics": metrics, "stats_at": self.broker_stats_at})
            return

        received_at = utc_now()
        payload = self._decode_payload(message.payload)
        telemetry_point = None
        if message.topic == "factory/line-01/machine-01/telemetry" and payload["kind"] == "json" and not payload["truncated"]:
            try:
                decoded = json.loads(payload["value"])
                if isinstance(decoded, dict) and decoded.get("device_id") == "machine-01":
                    temperature = decoded.get("temperature_c")
                    vibration = decoded.get("vibration_mm_s")
                    try:
                        temperature_value = float(temperature)
                        vibration_value = float(vibration)
                    except (TypeError, ValueError, OverflowError):
                        temperature_value = vibration_value = float("nan")
                    if (isinstance(temperature, (int, float)) and not isinstance(temperature, bool)
                            and math.isfinite(temperature_value) and isinstance(vibration, (int, float))
                            and not isinstance(vibration, bool) and math.isfinite(vibration_value)):
                        telemetry_point = {
                            "received_at": received_at,
                            "temperature_c": temperature_value,
                            "vibration_mm_s": vibration_value,
                        }
            except (json.JSONDecodeError, RecursionError):
                pass

        with self.lock:
            self.sequence += 1
            item = {
                "id": self.sequence,
                "received_at": received_at,
                "topic": message.topic,
                "qos": int(message.qos),
                "retained": bool(message.retain),
                "payload": payload,
                "telemetry": telemetry_point,
                # Only the firmware publishes this topic (ACL); used for the firmware-only counters.
                "from_firmware": message.topic == FIRMWARE_TOPIC,
            }
            self.messages.append(item)
            self.last_message_at = received_at
            if item["from_firmware"]:
                self.firmware_messages += 1
                self.firmware_last_seen_at = received_at
            if telemetry_point is not None:
                self.telemetry.append(telemetry_point)
                now = time.monotonic()
                self.telemetry_times.append(now)
                while self.telemetry_times and now - self.telemetry_times[0] > 10:
                    self.telemetry_times.popleft()
                elapsed = now - self.telemetry_times[0] if len(self.telemetry_times) > 1 else 0
                self.telemetry_rate = (len(self.telemetry_times) - 1) / elapsed if elapsed > 0 else 0.0
            rate = self.telemetry_rate
        self._emit("message", item)
        if telemetry_point is not None:
            self._emit("rate", {"telemetry_rate": rate})


monitors = {
    "plain": Monitor("plain", os.getenv("MQTT_HOST", "broker"), int(os.getenv("MQTT_PORT", "1883"))),
    "tls": Monitor("tls", os.getenv("MQTT_TLS_HOST", "broker_tls"), int(os.getenv("MQTT_TLS_PORT", "8883")),
                   os.getenv("MQTT_TLS_CA", "/certs/ca.crt")),
}


def pick(broker: str) -> Monitor:
    if broker not in monitors:
        raise HTTPException(status_code=404, detail="Broker không tồn tại")
    return monitors[broker]


@asynccontextmanager
async def lifespan(app: FastAPI):
    for monitor in monitors.values():
        monitor.start()
    yield
    for monitor in monitors.values():
        monitor.stop()


app = FastAPI(title="MQTT LAB Dashboard", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {"ok": True, "brokers": {name: m.state()["broker"]["connected"] for name, m in monitors.items()}}


@app.get("/api/state")
async def get_state(broker: str = "plain") -> dict[str, Any]:
    return pick(broker).state()


@app.get("/api/events")
async def events(request: Request, broker: str = "plain") -> StreamingResponse:
    monitor = pick(broker)
    queue = monitor.add_sse_client()

    async def stream():
        try:
            snapshot = monitor.state()
            yield "event: snapshot\ndata: " + json.dumps(snapshot, separators=(",", ":")) + "\n\n"
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                if event is None:
                    return
                yield "event: " + event["type"] + "\ndata: " + json.dumps(event["data"], separators=(",", ":")) + "\n\n"
        finally:
            monitor.remove_sse_client(queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if (STATIC_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{path:path}")
async def frontend(path: str) -> FileResponse:
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=503, detail="Dashboard frontend chưa được build")
    return FileResponse(index)
