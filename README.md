# MQTT LAB

Lab MQTT 3.1.1 trên Debian Linux/WSL, Mosquitto, firmware ESP32 DevKit và dashboard realtime FastAPI + Vue. Hướng dẫn setup/run được tách theo từng phần trong [`docs/setup/`](docs/setup/README.md).

## Bắt đầu nhanh

1. Làm theo [01 — Environment and Docker](docs/setup/01-environment.md).
2. Làm theo [02 — Broker](docs/setup/02-broker.md).
3. Cấu hình/nạp ESP32 theo [03 — ESP32 Firmware](docs/setup/03-esp32-firmware.md).
4. Chạy dashboard: `./run.sh dashboard --firmware`, hoặc thu baseline PCAP bằng `./run.sh`.

## Hướng dẫn theo phần

- [Setup guide index](docs/setup/README.md)
- [Environment and Docker](docs/setup/01-environment.md)
- [Broker](docs/setup/02-broker.md)
- [ESP32 DevKit firmware](docs/setup/03-esp32-firmware.md)
- [Realtime dashboard](docs/setup/04-dashboard.md)
- [E00 baseline and PCAP analysis](docs/setup/05-baseline-pcap.md)

## Cấu trúc thư mục

```text
mqtt-lab/
├── capture/                 # tcpdump/tshark image
├── config/mosquitto/        # Mosquitto config and ACL source
├── dashboard/               # FastAPI backend and Vue frontend
├── docs/
│   ├── plan.md              # Kế hoạch dự án
│   ├── progress/            # Nhật ký tiến độ theo phase
│   ├── protocol-analysis.md # Phân tích MQTT/PCAP
│   └── setup/               # Hướng dẫn setup và chạy theo phần
├── firmware/mqtt_sensor/    # ESP32 DevKit firmware
├── lab_clients/             # MQTT subscriber và auth/ACL test client
├── scripts/                 # Khởi tạo, kiểm tra, capture và phân tích
├── compose.yaml             # Lab mặc định, broker không mở ra host
├── compose.firmware.yaml    # Override mạng/cổng cho thiết bị ESP32
├── run.sh                   # Lệnh chạy dashboard hoặc baseline
└── README.md                # Tổng quan dự án và quick start
```

Sơ đồ triển khai và phạm vi các phase xem tại [docs/plan.md](docs/plan.md); tiến độ trong [docs/progress/](docs/progress/).
