# Quan sát MQTT bằng Wireshark trên Windows

## Bắt gói từ ESP32 tới Mosquitto

Broker lab hiện nhận MQTT plaintext qua TCP port `1883`, tại `192.168.100.102`. Khi ESP32 gửi telemetry qua cùng mạng Wi‑Fi:

1. Mở Wireshark và vào **Capture → Options…**.
2. Chọn giao diện **Wi‑Fi** để bắt lưu lượng trên mạng LAN. Không chọn `vEthernet (WSL)` cho luồng ESP32 → địa chỉ Wi‑Fi của máy.
3. Bắt đầu capture khi ESP32 đang kết nối và publish dữ liệu.
4. Nhập display filter:

   ```wireshark
   tcp.port == 1883
   ```

   Bộ lọc này hiện cả hai chiều. Để chỉ xem gói đi tới broker, dùng `tcp.dstport == 1883`.

## Đọc bản tin PUBLISH

Chọn một dòng có Protocol là **MQTT** và Info là **Publish Message**. Trong capture kiểm chứng ngày 17/10/2026, gói được quan sát có:

- Source `192.168.100.127` (ESP32) và destination `192.168.100.102` (broker).
- Topic `factory/line-01/machine-01/telemetry`.
- QoS 1 (At least once delivery).
- Payload JSON telemetry; nội dung có thể đọc được trong MQTT details hoặc vùng ASCII ở khung bytes bên phải.
- Message Identifier tăng dần trong các PUBLISH QoS 1 được quan sát.

TCP có thể chia một MQTT message thành nhiều segment. Wireshark thường hiển thị segment TCP và dòng MQTT đã được ráp lại; chọn dòng MQTT **Publish Message** để xem nội dung đã giải mã.

## Lưu ý khi phân tích

- Nếu filter hợp lệ nhưng không hiện gói, xác nhận đang capture đúng giao diện Wi‑Fi, ESP32 đang publish, và destination là máy chạy broker. Màu xanh của filter chỉ xác nhận cú pháp hợp lệ; `Displayed: 0` nghĩa là capture hiện tại không có gói khớp.
- Thông báo `Unknown Version (missing the CONNECT packet?)` có thể xuất hiện khi bắt đầu capture sau handshake MQTT. Nó không tự nó chứng minh PUBLISH sai. Bắt đầu capture trước khi ESP32 kết nối nếu cần phân tích cả CONNECT/CONNACK.
- Port `1883` không mã hóa MQTT. PCAP có thể chứa topic, payload và dữ liệu xác thực từ CONNECT; không chia sẻ PCAP chưa rà soát.
- Wireshark trên Windows phù hợp để học và xem PCAP. Với baseline có thể tái lập của lab, dùng capture trong network namespace của broker rồi mở PCAP bằng Wireshark.
