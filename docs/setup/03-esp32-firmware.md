# 3. Firmware ESP32 DevKit

## Cấu hình biến môi trường

Mẫu biến nằm trong `.env.firmware.example`. Tạo file riêng để giữ bí mật khỏi Git:

```bash
cp .env.firmware.example .env.firmware
chmod 600 .env.firmware
${EDITOR:-nano} .env.firmware
```

Điền Wi-Fi 2.4 GHz, `MQTT_HOST` và `BROKER_BIND_IP` bằng IP LAN của máy chạy broker. `MQTT_USERNAME`/`MQTT_PASSWORD` phải khớp `SENSOR_USERNAME`/`SENSOR_PASSWORD` trong `.env`. Nếu để nguyên giá trị mẫu cho `MQTT_PASSWORD`, generator sẽ tự lấy `SENSOR_PASSWORD` từ `.env`; credential thật không được đưa vào lab.

Sinh header cho Arduino:

```bash
python3 scripts/generate_firmware_config.py
```

Header `firmware/mqtt_sensor/firmware_config.h` được sinh tự động và bị Git bỏ qua.

## Build và nạp từ Debian bằng Arduino CLI

### 1. Cài Arduino CLI, ESP32 core và thư viện

```bash
sudo apt update
sudo apt install -y curl
mkdir -p ~/.local/bin
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh \
  | BINDIR="$HOME/.local/bin" sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

arduino-cli config init --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core update-index
arduino-cli core install esp32:esp32
arduino-cli lib install ArduinoMqttClient
```

Arduino CLI cài binary vào `~/.local/bin`; Espressif cung cấp board core qua package index riêng. [Arduino CLI install](https://arduino.github.io/arduino-cli/latest/installation/), [Espressif Arduino-ESP32 setup](https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html).

### 2. Chuyển cổng USB từ Windows sang WSL (chỉ WSL)

Windows không tự đưa USB serial device vào Debian/WSL. Cài `usbipd-win` một lần trong PowerShell:

```powershell
winget install --interactive --exact dorssel.usbipd-win
```

Cắm ESP32. Trong **PowerShell chạy với quyền Administrator**, tìm thiết bị và bind BUSID của board (ví dụ `4-4`):

```powershell
usbipd list
usbipd bind --busid 4-4
```

Sau đó trong PowerShell bình thường, attach thiết bị vào WSL:

```powershell
usbipd attach --wsl --busid 4-4
```

Thay `4-4` bằng BUSID thực tế. Mở terminal Debian và xác nhận board xuất hiện:

```bash
arduino-cli board list
```

Microsoft lưu ý thiết bị USB đang attach vào WSL sẽ không dùng được bởi ứng dụng Windows cho tới khi detach. [Hướng dẫn USB trong WSL](https://learn.microsoft.com/windows/wsl/connect-usb).

### 3. Compile, upload và xem Serial Monitor

Bạn đã tạo `firmware/mqtt_sensor/firmware_config.h` bằng `python3 scripts/generate_firmware_config.py`. Cắm/attach board trước, lấy cổng từ `arduino-cli board list` (thường `/dev/ttyUSB0` hoặc `/dev/ttyACM0`), rồi chạy từ thư mục repo:

```bash
arduino-cli compile --fqbn esp32:esp32:esp32 firmware/mqtt_sensor
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32 firmware/mqtt_sensor
arduino-cli monitor -p /dev/ttyUSB0 --config baudrate=115200
```

Thay `/dev/ttyUSB0` bằng cổng thực tế. Board identifier `esp32:esp32:esp32` tương ứng ESP32 Dev Module. CLI compile và upload là hai lệnh riêng. [Arduino CLI compile/upload](https://arduino.github.io/arduino-cli/latest/getting-started/).

Nếu báo `Permission denied` với cổng serial:

```bash
sudo usermod -aG dialout "$USER"
```

Đóng/mở lại terminal Debian rồi thử lại. Khi broker đang chạy, Serial Monitor ở 115200 baud cần in `MQTT_CONNECTED` và các dòng `PUBLISH_ACKED`.

Bạn cũng có thể dùng Arduino IDE nếu thích giao diện đồ họa; chọn ESP32 Dev Module, chọn cùng cổng serial và dùng baud rate 115200 cho Serial Monitor.

Firmware phát telemetry JSON cho `machine-01` mỗi giây, MQTT 3.1.1 QoS 1.

## Kết nối thiết bị

Khởi chạy broker và dashboard cho LAN:

```bash
./run.sh dashboard --firmware
```

Mở dashboard tại `http://localhost:8081`. Nếu chỉ thu PCAP, dùng `./run.sh` và reset ESP32 khi runner báo capture đã sẵn sàng. Firewall máy host cần cho phép TCP/1883 trên giao diện mạng lab. MQTT không mã hóa; chỉ dùng mạng thử nghiệm riêng.

Khi xong, dừng dashboard bằng `./run.sh dashboard stop`; dừng cả broker bằng lệnh `docker compose ... down` tại [02 — Broker](02-broker.md).
