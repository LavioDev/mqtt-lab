#!/usr/bin/env python3
"""Index selected MQTT control packets in one baseline PCAP using tshark."""

from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKET_TYPES = {"1": "CONNECT", "2": "CONNACK", "3": "PUBLISH", "4": "PUBACK",
                "8": "SUBSCRIBE", "9": "SUBACK", "12": "PINGREQ", "13": "PINGRESP", "14": "DISCONNECT"}
REQUIRED = ("CONNECT", "CONNACK", "SUBSCRIBE", "SUBACK", "PUBLISH")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    args = parser.parse_args()
    pcap = ROOT / "data" / "raw" / args.run_id / "baseline.pcap"
    if not pcap.is_file():
        parser.error(f"PCAP not found: {pcap}")
    command = [
        "docker", "run", "--rm", "--network", "none", "-v", f"{pcap.resolve()}:/capture.pcap:ro",
        "mqtt-lab-capture:phase1", "tshark", "-r", "/capture.pcap", "-Y", "mqtt",
        "-T", "fields", "-E", "separator=,", "-E", "quote=d", "-E", "occurrence=f",
        "-e", "frame.number", "-e", "frame.time_epoch", "-e", "ip.src", "-e", "ip.dst",
        "-e", "mqtt.msgtype", "-e", "mqtt.clientid", "-e", "mqtt.topic",
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
    rows = []
    for values in csv.reader(io.StringIO(result.stdout)):
        if len(values) != 7:
            continue
        frame, time_epoch, source, destination, msgtype, client_id, topic = values
        try:
            packet_type = PACKET_TYPES[str(int(msgtype, 0))]
        except (ValueError, KeyError):
            continue
        rows.append({"frame": int(frame), "time_epoch": time_epoch, "source_ip": source,
                     "destination_ip": destination, "type": packet_type,
                     "client_id": client_id or None, "topic": topic or None})
    first_frames = {packet_type: next((row for row in rows if row["type"] == packet_type), None)
                    for packet_type in REQUIRED}
    report = {"run_id": args.run_id, "packet_count": len(rows), "first_frames": first_frames,
              "type_counts": {kind: sum(row["type"] == kind for row in rows) for kind in PACKET_TYPES.values()}}
    output = pcap.parent / "packet-index.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for packet_type, row in first_frames.items():
        print(f"{packet_type:10} frame {row['frame'] if row else 'MISSING'}")
    print(f"Index: {output}")
    return 0 if all(first_frames.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
