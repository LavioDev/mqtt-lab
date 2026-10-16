# MQTT LAB — Hướng dẫn setup

Thực hiện các hướng dẫn theo thứ tự. Mỗi trang bao gồm cấu hình cần thiết, lệnh chạy và cách dừng phần tương ứng.

| Phần | Hướng dẫn | Dùng khi |
|---|---|---|
| 1 | [Environment and Docker](01-environment.md) | Cài/chạy lab lần đầu trên Debian Linux hoặc WSL2 |
| 2 | [Broker](02-broker.md) | Tạo credential, ACL, chạy Mosquitto và kiểm tra quyền |
| 3 | [ESP32 DevKit firmware](03-esp32-firmware.md) | Cấu hình Wi-Fi/MQTT, build và nạp firmware |
| 4 | [Realtime dashboard](04-dashboard.md) | Theo dõi telemetry và trạng thái broker trên trình duyệt |
| 5 | [E00 baseline and PCAP](05-baseline-pcap.md) | Thu 60 bản tin thật từ ESP32, lưu và phân tích capture |

## Lệnh thường dùng

```bash
./run.sh dashboard --firmware # dashboard + broker cho ESP32
./run.sh                     # kiểm tra ACL và thu baseline từ ESP32
./run.sh dashboard stop      # dừng dashboard; broker vẫn chạy
```

Nếu chỉ cần broker cô lập trong Docker, không mở cổng cho ESP32, xem [Broker](02-broker.md). Quay lại [README dự án](../../README.md).
