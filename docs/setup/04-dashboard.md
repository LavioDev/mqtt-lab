# 4. Dashboard realtime

Dashboard dùng Vue 3 + TypeScript ở frontend và FastAPI + paho-mqtt ở backend. FastAPI đẩy dữ liệu qua SSE; database không dùng ở phiên bản này.

## Chạy

Chỉ truy cập từ máy hiện tại, broker không mở cổng LAN:

```bash
./run.sh dashboard
```

Để vừa theo dõi vừa kết nối ESP32 qua LAN:

```bash
./run.sh dashboard --firmware
```

Mở `http://localhost:8081` (hoặc port `DASHBOARD_PORT` đã cấu hình). Chạy `./run.sh dashboard stop` để dừng dashboard/proxy; broker đang chạy sẽ được giữ lại.

Khi nâng cấp từ stack cũ tên `mqtt-sentinel`, `run.sh` sẽ tự dọn stack cũ để giải phóng port trước khi khởi chạy dashboard mới tên `mqtt-lab`.

## Màn hình và trạng thái

- Trạng thái riêng cho trình duyệt ↔ backend và backend ↔ broker.
- Thống kê Mosquitto lấy từ `$SYS`; số client tính cả dashboard monitor.
- Biểu đồ temperature/vibration và danh sách bản tin `factory/#`.
- Lịch sử RAM tối đa 200 bản tin, tối đa 120 điểm trên mỗi biểu đồ; restart backend sẽ xóa lịch sử.
- Dashboard chỉ đọc; credential MQTT chỉ được dùng ở backend. Không có đăng nhập dashboard.

Kiểm tra nhanh API:

```bash
curl -fsS http://localhost:8081/healthz
curl -fsS http://localhost:8081/api/state
```

Firmware đang chạy thì dữ liệu sẽ tự xuất hiện qua SSE, không cần tải lại trang.
