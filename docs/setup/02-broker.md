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
