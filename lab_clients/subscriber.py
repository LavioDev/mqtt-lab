"""Record telemetry received during a baseline run."""

from __future__ import annotations

import json
import signal
import threading
import time

from lab_clients.common import TOPIC, EventWriter, connect_and_wait, disconnect, make_client, required


def main() -> None:
    run_id = required("RUN_ID")
    events = EventWriter("subscriber.jsonl")
    connected = threading.Event()
    subscribed = threading.Event()
    stopped = threading.Event()
    errors: list[str] = []
    client = make_client(f"subscriber-{run_id}", "SUBSCRIBER_USERNAME", "SUBSCRIBER_PASSWORD")

    def on_connect(current_client, _userdata, _flags, reason_code, _properties):
        events.write("connect", reason_code=str(reason_code))
        if reason_code.is_failure:
            errors.append(f"Subscriber authentication failed: {reason_code}")
        else:
            current_client.subscribe(TOPIC, qos=1)
        connected.set()

    def on_subscribe(_client, _userdata, _mid, reason_codes, _properties):
        if any(code.is_failure for code in reason_codes):
            errors.append(f"Subscription rejected: {reason_codes}")
        else:
            events.write("subscribed", topic=TOPIC, qos=1)
            print("SUBSCRIBED", flush=True)
        subscribed.set()

    def on_message(_client, _userdata, message):
        try:
            payload = json.loads(message.payload)
            message_id = payload.get("message_id")
        except (ValueError, UnicodeDecodeError):
            message_id = None
        events.write("message", message_id=message_id, topic=message.topic, qos=message.qos)

    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    try:
        connect_and_wait(client, connected, errors)
        if not subscribed.wait(15):
            raise TimeoutError("Timed out waiting for SUBACK")
        if errors:
            raise RuntimeError(errors[0])
        while not stopped.is_set():
            time.sleep(0.2)
    finally:
        disconnect(client)
        events.close()


if __name__ == "__main__":
    main()
