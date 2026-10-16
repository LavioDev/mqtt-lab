# 5. Baseline E00 và phân tích PCAP

Baseline mới dùng telemetry thật từ firmware ESP32, không có sensor simulator. Trước khi chạy, hoàn tất [03 — Firmware ESP32](03-esp32-firmware.md), upload firmware và đặt thiết bị trong cùng mạng với broker.

## Thu baseline

Tại thư mục gốc:

```bash
./run.sh
```

Lệnh khởi tạo credential, chạy kiểm tra auth/ACL, mở broker trên `BROKER_BIND_IP`, rồi bật tcpdump và subscriber. Khi terminal báo `Capture ready`, reset hoặc bật ESP32. Runner đợi tối đa 120 giây để subscriber nhận đủ 60 bản tin QoS 1.

Có thể đặt run ID và timeout riêng:

```bash
python3 scripts/run_baseline.py --run-id E00-ESP32-01 --timeout 150
```

Mỗi ID chỉ chạy một lần vì artifact không bị ghi đè. Kết quả nằm ở `data/raw/<run_id>/`: PCAP, log broker/capture/subscriber, `subscriber.jsonl` và `manifest.json`.

## Lập chỉ mục và đọc PCAP

```bash
python3 scripts/analyze_pcap.py E00-ESP32-01
```

Lệnh tạo `packet-index.json`, gồm số frame đầu tiên và tổng số frame của CONNECT, CONNACK, PUBLISH, SUBSCRIBE, SUBACK cùng một số control packet khác. Mở `baseline.pcap` bằng Wireshark và dùng filter `mqtt` hoặc `mqtt.msgtype == 3`.

Phân tích packet lịch sử và cách diễn giải ACL xem trong [docs/protocol-analysis.md](../protocol-analysis.md). Các run E00-R02/R03 được ghi trong [tiến độ Phase 1](../progress/phase-1.md) là capture cũ từ simulator, không phải baseline firmware.

## Dọn tài nguyên

Runner dọn Compose project riêng sau khi thu log. Để dừng các service còn chạy:

```bash
docker compose --env-file .env --env-file .env.firmware \
  -f compose.yaml -f compose.firmware.yaml down
```

Không commit `data/raw/`: PCAP lưu credential lab và payload plaintext.
