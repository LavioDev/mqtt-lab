# ESP32 DevKit firmware — nhật ký triển khai

## Trạng thái

- Firmware mẫu và cấu hình môi trường đã được thêm.
- Chưa xác nhận compile/upload hoặc kết nối phần cứng; cần điền Wi-Fi, IP LAN, credential và thử trên ESP32 DevKit thật.
- Runner E00 đã được chuyển sang thu 60 bản tin từ firmware; compile/upload phần cứng chưa kiểm chứng trong workspace.

## Đã triển khai

- `firmware/mqtt_sensor/mqtt_sensor.ino`: sketch Arduino kết nối Wi-Fi, đăng nhập broker và gửi telemetry tổng hợp theo chu kỳ, MQTT 3.1.1 QoS 1.
- `.env.firmware.example` và `.env.firmware`: biến cấu hình riêng cho firmware; file có bí mật và header sinh ra đều bị Git bỏ qua.
- `scripts/generate_firmware_config.py`: sinh header Arduino từ `.env.firmware`.
- `compose.firmware.yaml`: override bind TCP/1883 vào `BROKER_BIND_IP`; Compose mặc định vẫn không publish cổng broker.
- README có hướng dẫn điền biến, tạo header, compile/upload và chạy broker cho thiết bị.

## Bước xác nhận còn lại

1. Điền `.env.firmware`; đặt `MQTT_HOST` và `BROKER_BIND_IP` bằng IP LAN của máy Docker; dùng đúng credential sensor trong `.env`.
2. Chạy `python3 scripts/generate_firmware_config.py`, compile/upload sketch bằng Arduino IDE với ESP32 board support và ArduinoMqttClient.
3. Chạy broker bằng override firmware, mở Serial Monitor ở 115200 baud và xác nhận `MQTT_CONNECTED` cùng `PUBLISH_ACKED`.
4. Bắt PCAP và đối chiếu QoS 1/PUBACK cùng log subscriber.

## Giới hạn hiện tại

- Firmware dùng Wi-Fi 2.4 GHz và MQTT plaintext trong mạng lab.
- Broker access từ thiết bị phụ thuộc mạng LAN/firewall Windows; chưa được kiểm chứng trong môi trường phần cứng người dùng.
- Sensor simulator Python đã được gỡ; baseline E00 mới nhận telemetry trực tiếp từ ESP32. Các PCAP E00-R02/R03 trong báo cáo Phase 1 là artifact lịch sử từ simulator, không phải capture firmware.
