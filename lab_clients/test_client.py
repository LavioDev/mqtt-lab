"""One-shot checks for the lab account and ACL."""

from __future__ import annotations

import argparse
import json
import os
import threading
import time

import paho.mqtt.client as mqtt

from lab_clients.common import STATUS_TOPIC, TOPIC, connect_and_wait, disconnect, make_client, required


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["probe", "anonymous", "wrong-password", "acl-deny", "monitor-probe", "telemetry-smoke"])
    mode = parser.parse_args().mode
    ready = threading.Event()
    subscribed = threading.Event()
    outcome: list[bool] = []
    client_prefix = "monitor" if mode == "monitor-probe" else "sensor" if mode == "telemetry-smoke" else "test"
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"{client_prefix}-{required('RUN_ID')}-{mode}",
        clean_session=True,
        protocol=mqtt.MQTTv311,
    )
    if os.environ.get("MQTT_TLS_CA"):
        client.tls_set(ca_certs=os.environ["MQTT_TLS_CA"])
    if mode == "telemetry-smoke":
        client.username_pw_set(required("SENSOR_USERNAME"), required("SENSOR_PASSWORD"))
    elif mode not in {"anonymous", "monitor-probe"}:
        password = required("TEST_CLIENT_PASSWORD") if mode != "wrong-password" else "deliberately-wrong-password"
        client.username_pw_set(required("TEST_CLIENT_USERNAME"), password)
    elif mode == "monitor-probe":
        client.username_pw_set(required("MONITOR_USERNAME"), required("MONITOR_PASSWORD"))

    if mode == "monitor-probe":
        sys_seen = threading.Event()
        telemetry_seen = threading.Event()

        def on_monitor_connect(_client, _userdata, _flags, reason_code, _properties):
            if reason_code.is_failure:
                ready.set()
                outcome.append(False)
                return
            _client.subscribe([("factory/#", 1), ("$SYS/broker/#", 1)])

        def on_monitor_subscribe(_client, _userdata, _mid, reason_codes, _properties):
            outcome.append(all(not code.is_failure for code in reason_codes))
            subscribed.set()

        def on_monitor_message(_client, _userdata, message):
            if message.topic.startswith("$SYS/broker/"):
                sys_seen.set()
            elif message.topic == TOPIC:
                telemetry_seen.set()

        client.on_connect = on_monitor_connect
        client.on_subscribe = on_monitor_subscribe
        client.on_message = on_monitor_message
        try:
            client.connect(os.environ.get("MQTT_HOST", "broker"), int(os.environ.get("MQTT_PORT", "1883")), 30)
            client.loop_start()
            if not subscribed.wait(10) or not outcome[-1]:
                raise RuntimeError("Monitor ACL did not allow required subscriptions")
            if not sys_seen.wait(10):
                raise RuntimeError("Monitor could not read Mosquitto $SYS statistics")

            sensor = make_client(f"sensor-{required('RUN_ID')}-monitor-probe", "SENSOR_USERNAME", "SENSOR_PASSWORD")
            sensor_ready = threading.Event()
            sensor_errors: list[str] = []
            sensor.on_connect = lambda _c, _u, _f, rc, _p: (sensor_errors.append(str(rc)) if rc.is_failure else None, sensor_ready.set())
            connect_and_wait(sensor, sensor_ready, sensor_errors, timeout=10)
            try:
                info = sensor.publish(TOPIC, json.dumps({"device_id": "machine-01", "temperature_c": 42.5, "vibration_mm_s": 2.1}), qos=1)
                info.wait_for_publish(timeout=10)
            finally:
                disconnect(sensor)
            if not telemetry_seen.wait(10):
                raise RuntimeError("Monitor could not read authorized telemetry")

            attempted = client.publish(TOPIC, "monitor-must-not-publish", qos=1)
            if attempted.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(f"Could not send ACL denial probe: {attempted.rc}")
            print("MONITOR_READ_OK telemetry_and_sys", flush=True)
            print("MONITOR_PUBLISH_DENIAL_PROBE_SENT", flush=True)
        finally:
            disconnect(client)
        return

    def on_connect(_client, _userdata, _flags, reason_code, _properties):
        outcome.append(not reason_code.is_failure)
        ready.set()

    def on_subscribe(_client, _userdata, _mid, reason_codes, _properties):
        outcome.append(all(not code.is_failure for code in reason_codes))
        subscribed.set()

    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    try:
        client.connect(os.environ.get("MQTT_HOST", "broker"), int(os.environ.get("MQTT_PORT", "1883")), 30)
        client.loop_start()
        if not ready.wait(10):
            raise TimeoutError("No CONNACK from broker")
        if mode in {"anonymous", "wrong-password"}:
            if outcome[0]:
                raise RuntimeError(f"{mode} connection unexpectedly accepted")
            print(f"EXPECTED_AUTH_REJECTION {mode}", flush=True)
            return
        if not outcome[0]:
            raise RuntimeError("Valid test account was rejected")
        if mode == "probe":
            result, _mid = client.subscribe(STATUS_TOPIC, qos=1)
            if result != mqtt.MQTT_ERR_SUCCESS or not subscribed.wait(10):
                raise RuntimeError("SUBACK not received")
            if not outcome[-1]:
                raise RuntimeError("Allowed subscription failed")
            print("PROBE_OK", flush=True)
        elif mode == "telemetry-smoke":
            payload = json.dumps({
                "message_id": "dashboard-smoke-000001", "device_id": "machine-01",
                "temperature_c": 42.5, "vibration_mm_s": 2.1,
            })
            info = client.publish(TOPIC, payload, qos=1)
            info.wait_for_publish(timeout=10)
            print("DASHBOARD_SMOKE_TELEMETRY_SENT", flush=True)
        else:
            info = client.publish(TOPIC, "synthetic-acl-deny-probe", qos=1)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(f"Failed to send ACL probe: {info.rc}")
            info.wait_for_publish(timeout=10)
            print("ACL_TEST_PUBLISH_SENT", flush=True)
    finally:
        disconnect(client)


if __name__ == "__main__":
    main()
