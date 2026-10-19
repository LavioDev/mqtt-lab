# 2. Broker Mosquitto và quyền truy cập

## Cấu hình

`config/mosquitto/mosquitto.conf` cấu hình listener MQTT 3.1.1 trên cổng 1883 và nạp password/ACL runtime từ `config/mosquitto/auth/`. Chạy `python3 scripts/init_lab.py` để khởi tạo hoặc đồng bộ credential. Credential `.env` là giả lập dùng riêng cho lab.

ACL mặc định giới hạn sensor chỉ ghi telemetry của `machine-01`, subscriber chỉ đọc telemetry đó, test client chỉ đọc status; dashboard dùng tài khoản monitor chỉ đọc `factory/#` và `$SYS/broker/#`.

## Chạy broker trong mạng cô lập

```bash
docker compose up -d broker
docker compose ps
```

Compose mặc định đặt broker trong mạng `internal: true`, không publish cổng ra host. Container lab kết nối tới hostname `broker:1883`.

Kiểm tra auth và ACL:

```bash
python3 scripts/verify_lab.py
```

Kết quả mong đợi: tài khoản hợp lệ được chấp nhận, anonymous và password sai bị từ chối, PUBLISH ngoài ACL bị từ chối trong broker log.

## Mở broker cho ESP32 trên LAN

Chỉ khi cần kết nối thiết bị, điền `BROKER_BIND_IP` trong `.env.firmware` bằng IP máy chạy Docker có thể truy cập từ ESP32. Khởi động qua `./run.sh dashboard --firmware` hoặc baseline `./run.sh`; override này gắn broker thêm vào mạng `firmware_edge` và bind cổng 1883 vào IP cấu hình. Mạng `lab` nội bộ vẫn giữ cho các service khác. Không bind ra `0.0.0.0`.

## Dừng broker

Mạng cô lập:

```bash
docker compose down
```

Với override firmware:

```bash
docker compose --env-file .env --env-file .env.firmware \
  -f compose.yaml -f compose.firmware.yaml down
```

## Listener TLS 8883

`python3 scripts/init_lab.py` tạo CA tự ký (`ca.crt`/`ca.key`) một lần và chứng chỉ broker (`server.crt`/`server.key`) trong `config/mosquitto/auth/tls/` (bị Git bỏ qua). SAN của chứng chỉ gồm `localhost`, `broker`, `127.0.0.1` và `MQTT_HOST` trong `.env.firmware`; đổi `MQTT_HOST` rồi chạy lại script sẽ cấp lại chứng chỉ broker mà vẫn giữ CA. Listener 8883 dùng TLS 1.2+ cùng user/password và ACL như cổng 1883; override firmware bind 8883 vào `BROKER_BIND_IP`. Kiểm tra:

```bash
openssl s_client -connect "$BROKER_BIND_IP:8883" -CAfile config/mosquitto/auth/tls/ca.crt -verify_return_error </dev/null
```

Chỉ dùng cho test: private key của CA nằm cùng máy với broker.
