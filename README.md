# MQTT LAB

Lab MQTT 3.1.1 chạy hoàn toàn trong Docker: broker Mosquitto (plaintext 1883 và TLS 8883), firmware ESP32 DevKit và dashboard realtime FastAPI + Vue. Toàn bộ hướng dẫn setup/chạy nằm trong file này; kế hoạch và phân tích nằm ở [docs/](docs/).

## 1. Yêu cầu

- Docker Desktop (Linux containers) hoặc Docker Engine + Compose v2. **Không** cần Python, bash hay arduino-cli trên host.
- Mọi lệnh đi qua launcher `lab`:
  - bash/WSL/Linux/Git Bash: `./lab.sh <lệnh>`
  - PowerShell: `.\lab.ps1 <lệnh>`
- Launcher build image `tools` (Python, Docker CLI, mosquitto_passwd, openssl, tshark) và chạy script trong đó qua `docker.sock`; repo được mount tại chính đường dẫn host để compose lồng nhau hoạt động. Docker socket cho container `tools` quyền root trên host, chỉ dùng cho lab cục bộ.
- Các ví dụ dưới đây dùng `./lab.sh`; với PowerShell thay bằng `.\lab.ps1`.

| Lệnh | Việc làm |
| --- | --- |
| `init` | Tạo `.env`, hash password, ACL, CA và cert TLS |
| `verify` | Kiểm tra mạng cô lập, auth, ACL, TLS |
| `dashboard [stop] [--firmware]` | Bật/tắt broker + dashboard |
| `baseline [run-id]` | Thu baseline 60 bản tin từ ESP32 + PCAP |
| `analyze <run-id>` | Lập chỉ mục PCAP |
| `firmware-config` | Sinh header cho firmware từ `.env.firmware` |
| `firmware` / `firmware flash` | Compile / nạp firmware |

## 2. Khởi tạo lab

```bash
./lab.sh init
./lab.sh verify
```

`init` tạo:

- `.env`: credential giả lập cho sensor, subscriber, test client và monitor (không dùng mật khẩu thật).
- `config/mosquitto/auth/passwords` (đã băm) và `acl.conf` (sinh từ mẫu `config/mosquitto/acl.conf`, chủ sở hữu uid 1883, quyền 600).
- CA riêng của lab và cert server cho broker TLS: `config/mosquitto/certs/` (`ca.crt`, `server.crt`, `server.key`) và khóa CA `data/pki/ca.key` (không mount vào broker).

Các file trên đều bị Git bỏ qua. Chạy lại `init` an toàn (idempotent); sau khi sửa ACL nguồn hoặc đổi IP trong `.env.firmware`, chạy lại để cập nhật. Muốn đổi CA thì xóa `data/pki/` và `config/mosquitto/certs/` rồi chạy `init` (phải nạp lại firmware).

`verify` kiểm tra: mạng `lab` là `internal`, broker không publish cổng ra host, tài khoản hợp lệ được nhận, kết nối TLS xác thực CA, anonymous/password sai bị từ chối, PUBLISH ngoài ACL bị từ chối trong log broker, monitor đọc được telemetry và `$SYS` nhưng không publish được.

## 3. Broker và quyền truy cập

Có hai broker Mosquitto riêng, dùng chung file password/ACL:

| Service | Cổng | Cấu hình | Dùng cho |
| --- | --- | --- | --- |
| `broker` | 1883 plaintext | `config/mosquitto/mosquitto.conf` | Phân tích PCAP |
| `broker_tls` | 8883 TLS 1.2 | `config/mosquitto/mosquitto-tls.conf` | ESP32 dùng TLS |

ACL: sensor chỉ ghi `factory/line-01/machine-01/telemetry`, subscriber chỉ đọc topic đó, test client chỉ đọc `.../status`, monitor (dashboard) chỉ đọc `factory/#` và `$SYS/broker/#`.

Mặc định cả hai broker nằm trong mạng `internal: true`, không mở cổng ra host; container lab nối tới `broker:1883` / `broker_tls:8883`. Cert server có SAN `broker`, `broker_tls`, `localhost`, `127.0.0.1` cùng `MQTT_HOST`/`BROKER_BIND_IP` trong `.env.firmware`.

MQTT không mã hóa ở 1883; PCAP có thể chứa username, password lab và payload. Chỉ dùng mạng thử nghiệm riêng.

## 4. Cấu hình firmware ESP32

```bash
cp .env.firmware.example .env.firmware        # PowerShell: Copy-Item .env.firmware.example .env.firmware
```

Điền vào `.env.firmware`:

- `WIFI_SSID`, `WIFI_PASSWORD`: Wi-Fi 2.4 GHz.
- `MQTT_HOST` và `BROKER_BIND_IP`: IP LAN của máy chạy Docker (ESP32 phải truy cập được). Không bind ra `0.0.0.0`.
- `MQTT_USERNAME`/`MQTT_PASSWORD` khớp `SENSOR_USERNAME`/`SENSOR_PASSWORD` trong `.env`; để nguyên giá trị mẫu của `MQTT_PASSWORD` thì generator tự lấy `SENSOR_PASSWORD` từ `.env`.
- TLS: `MQTT_TLS=1` + `MQTT_PORT=8883` (mặc định), hoặc `MQTT_TLS=0` + `MQTT_PORT=1883` để dùng plaintext và đọc PCAP.

Chạy `./lab.sh init` trước (để có CA), rồi sinh header:

```bash
./lab.sh firmware-config
```

Header `firmware/mqtt_sensor/firmware_config.h` được sinh tự động, nhúng CA khi `MQTT_TLS=1` và bị Git bỏ qua. Với TLS, firmware đồng bộ giờ qua NTP (`pool.ntp.org`) để kiểm tra hạn cert, nên Wi-Fi cần ra Internet.

### Compile và nạp

```bash
./lab.sh firmware                                  # compile, binary ra firmware/build/
SERIAL_PORT=/dev/ttyUSB0 ./lab.sh firmware flash   # nạp (Linux/WSL2)
```

Image `firmware` chứa Arduino CLI, ESP32 core và ArduinoMqttClient (cache trong volume `arduino_cache`; lần đầu tải lâu). Nạp từ container cần USB truyền vào Linux/WSL2: trên Windows cài `usbipd-win` (`winget install --interactive --exact dorssel.usbipd-win`), rồi trong PowerShell quản trị `usbipd bind --busid <BUSID>`, sau đó `usbipd attach --wsl --busid <BUSID>` và chạy lệnh nạp từ WSL. Docker Desktop trên Windows thuần không chuyển USB vào container; có thể nạp `firmware/build/*.bin` bằng Arduino IDE/esptool. Serial Monitor 115200 baud cần in `MQTT_CONNECTED` và các dòng `PUBLISH_ACKED`. Firmware phát telemetry JSON `machine-01` mỗi giây, MQTT 3.1.1 QoS 1.

## 5. Dashboard

Vue 3 + TypeScript (frontend), FastAPI + paho-mqtt (backend), đẩy dữ liệu qua SSE; không dùng database.

```bash
./lab.sh dashboard               # chỉ truy cập từ máy hiện tại
./lab.sh dashboard --firmware    # đồng thời mở broker cho ESP32 trên LAN (cần .env.firmware)
./lab.sh dashboard stop          # dừng dashboard/proxy (thêm --firmware nếu đã bật); broker giữ lại
```

Mở http://localhost:8081 (đổi bằng `DASHBOARD_PORT`). Chỉ dùng lệnh `lab`; đừng bấm Play/Stop trong Docker Desktop vì nó bỏ qua profile và file compose phụ.

- Hai tab: **BROKER 1883 · PLAINTEXT** và **BROKER 8883 · TLS**, mỗi tab nối một broker riêng (API `?broker=plain|tls`). Firmware gửi vào cổng nào thì chỉ tab đó có dữ liệu.
- Thẻ "Thiết bị đang hoạt động": số `device_id` có telemetry trong 15 giây gần nhất; thẻ "IoT publish đã nhận": số bản tin PUBLISH trên `factory/#` kể từ khi dashboard khởi động. Bảng bản tin hiển thị tối đa 100 gói.
- Biểu đồ temperature/vibration và danh sách bản tin `factory/#`; lịch sử RAM tối đa 100 bản tin, 120 điểm/biểu đồ, restart backend sẽ xóa.
- Dashboard chỉ đọc; credential MQTT chỉ dùng ở backend; không có đăng nhập dashboard.

Kiểm tra nhanh: `curl -fsS http://localhost:8081/healthz` và `curl -fsS "http://localhost:8081/api/state?broker=tls"`.

## 6. Baseline E00 và phân tích PCAP

Baseline dùng telemetry thật từ ESP32, không có simulator. Hoàn tất mục 4, nạp firmware và đặt thiết bị cùng mạng với broker. Để đọc được MQTT trong PCAP, đặt `MQTT_TLS=0` và `MQTT_PORT=1883` (PCAP của 8883 bị mã hóa).

```bash
./lab.sh baseline                 # hoặc ./lab.sh baseline E00-ESP32-01
```

Lệnh chạy `init` + `verify`, mở broker trên `BROKER_BIND_IP`, bật tcpdump và subscriber. Khi báo `Capture ready`, reset hoặc bật ESP32; runner đợi tối đa 120 giây để nhận đủ 60 bản tin QoS 1, rồi tự chạy `analyze`. Mỗi run ID chỉ dùng một lần. Kết quả ở `data/raw/<run_id>/`: `baseline.pcap`, log broker/capture/subscriber, `subscriber.jsonl`, `manifest.json`, `packet-index.json`.

Lập chỉ mục lại một run:

```bash
./lab.sh analyze E00-ESP32-01
```

`packet-index.json` ghi frame đầu tiên và tổng số CONNECT, CONNACK, PUBLISH, SUBSCRIBE, SUBACK cùng vài control packet khác. Mở `baseline.pcap` bằng Wireshark với filter `mqtt` hoặc `mqtt.msgtype == 3`. Diễn giải xem [docs/protocol-analysis.md](docs/protocol-analysis.md); các run E00-R02/R03 trong [docs/progress/phase-1.md](docs/progress/phase-1.md) là capture cũ từ simulator.

Không commit `data/raw/`: PCAP chứa credential lab và payload plaintext.

## 7. Dừng và dọn dẹp

```bash
./lab.sh dashboard stop           # chỉ dừng dashboard
docker compose down               # dừng broker và gỡ mạng (thêm --env-file .env --env-file .env.firmware -f compose.yaml -f compose.firmware.yaml nếu dùng --firmware)
```

## Cấu trúc thư mục

```text
mqtt-lab/
├── config/mosquitto/        # Cấu hình broker (plaintext + TLS), mẫu ACL; auth/ và certs/ sinh tự động
├── dashboard/               # FastAPI backend và Vue frontend
├── docker/                  # Dockerfile: tools, capture, firmware, dashboard, lab-client
├── docs/                    # Kế hoạch, tiến độ, phân tích giao thức
├── firmware/mqtt_sensor/    # Firmware ESP32 DevKit
├── lab_clients/             # MQTT subscriber và auth/ACL test client
├── scripts/                 # Khởi tạo, kiểm tra, capture, phân tích (chạy trong container tools)
├── compose.yaml             # Lab mặc định, broker không mở ra host
├── compose.firmware.yaml    # Override mở cổng 1883/8883 cho ESP32
├── compose.tools.yaml       # Container tools và firmware (arduino-cli)
├── lab.sh / lab.ps1         # Launcher Docker-only (bash / PowerShell)
└── README.md
```

Luồng end-to-end từ ESP32 tới broker, subscriber, PCAP và dashboard (kèm TCP ACK vs MQTT PUBACK trong Wireshark): [docs/mqtt-workflow.md](docs/mqtt-workflow.md). Sơ đồ triển khai và phạm vi các phase: [docs/plan.md](docs/plan.md); tiến độ: [docs/progress/](docs/progress/).
