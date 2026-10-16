# MQTT realtime dashboard — nhật ký triển khai

## Trạng thái

- **Hoàn thành triển khai và kiểm chứng integration.** Dashboard chạy tại `http://localhost:8081` trong môi trường hiện tại.
- Windows `httpd.exe` (PID 5816) đang giữ cổng 8080; host port cấu hình qua `DASHBOARD_PORT`, mặc định 8081. Debian thiếu Docker CLI nhưng script fallback dùng Docker Desktop Windows CLI.

## Đã triển khai

- `dashboard/backend/app.py`: một MQTT client đọc `factory/#` và `$SYS/broker/#`, giữ tối đa 200 message và 120 điểm telemetry, phát SSE có queue giới hạn và tự reconnect.
- `dashboard/frontend/`: giao diện Vue tiếng Việt với trạng thái kết nối, thống kê broker, biểu đồ telemetry và bảng lọc message.
- `dashboard/Dockerfile` và service profile `dashboard`: FastAPI phục vụ SPA cùng origin; Nginx gateway bind localhost, còn broker và FastAPI vẫn nằm trong mạng lab nội bộ.
- Mosquitto công bố `$SYS` mỗi 5 giây; ACL monitor chỉ cho đọc telemetry và thống kê.
- `scripts/init_lab.py` bổ sung credential monitor vào `.env` hiện có; `scripts/verify_lab.py` kiểm tra đọc telemetry/$SYS và từ chối PUBLISH monitor.
- `run.sh dashboard` khởi tạo auth rồi build/chạy broker, dashboard và gateway; `./run.sh dashboard stop` dừng dashboard/gateway. Script hỗ trợ Docker Desktop Windows CLI nếu WSL thiếu Docker CLI.

## Kiểm chứng

- `npm ci && npm run build` thành công; `npm audit` không báo lỗ hổng.
- Compose profile hợp lệ; lab network vẫn `internal: true`, broker không publish port, gateway bind `127.0.0.1:8081`.
- `./run.sh dashboard` build và khởi chạy thành công. `/healthz` trả `ok=true`, `/api/state` báo broker kết nối và có `$SYS` metrics.
- Publish telemetry thử QoS 1: API/SSE nhận JSON `machine-01`, nhiệt độ 42.5°C, rung 2.1 mm/s; hai SSE client độc lập cùng nhận snapshot.
- Restart broker phát trạng thái disconnect rồi reconnect; bridge tự subscribe lại và nhận `$SYS`.
- `scripts/verify_lab.py`: credential sensor cũ vẫn dùng được; monitor đọc telemetry/$SYS, broker từ chối PUBLISH; anonymous/mật khẩu sai vẫn bị từ chối.
- 4 unit test payload pass: JSON, HTML text, binary/base64 và giới hạn 64 KiB; `compileall` và `git diff --check` sạch.

## Bước tiếp theo

1. Thử giao diện responsive trong trình duyệt.
2. Điền `.env.firmware`; đặt `MQTT_HOST` và `BROKER_BIND_IP` theo IP LAN, dùng credential sensor trong `.env`.
3. Compile/upload sketch ESP32 DevKit, chạy `./run.sh dashboard --firmware`, rồi xác nhận `MQTT_CONNECTED`/`PUBLISH_ACKED` và telemetry.
4. Bắt PCAP và đối chiếu QoS 1/PUBACK cùng log subscriber.

## Giới hạn

- Chỉ truy cập từ máy local; dashboard chưa có đăng nhập riêng.
- Telemetry và lịch sử giữ trong RAM, mất khi dashboard khởi động lại.
- Chưa kiểm chứng với ESP32 vật lý. UI đã build; API/SSE kiểm thử bằng HTTP clients.
