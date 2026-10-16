# Phân tích MQTT plaintext — Phase 1

Nguồn chứng cứ lịch sử là PCAP E00 tại `data/raw/<run_id>/baseline.pcap`. Chạy `python3 scripts/analyze_pcap.py <run_id>` để tạo `packet-index.json`; mục `first_frames` ghi số frame thực tế. Bảng dưới đây lấy từ run **E00-R02** đã kiểm chứng trước khi gỡ simulator: 60 bản tin tổng hợp được gửi và nhận, PCAP 55.112 byte. Baseline mới nhận telemetry thật từ ESP32.

| Packet | Frame E00-R02 | Filter Wireshark | Quan sát được |
|---|---:|---|---|
| CONNECT | 4 | `mqtt.msgtype == 1` | MQTT version field `4` (3.1.1), Client ID `subscriber-E00-R02` |
| CONNACK | 6 | `mqtt.msgtype == 2` | Return code `0`, broker chấp nhận kết nối |
| SUBSCRIBE | 8 | `mqtt.msgtype == 8` | Yêu cầu topic `factory/line-01/machine-01/telemetry`, QoS 1 |
| SUBACK | 9 | `mqtt.msgtype == 9` | Granted QoS 1 cho yêu cầu trên |
| PUBLISH | 18 | `mqtt.msgtype == 3` | Cùng topic, QoS 1, `message_id` = `E00-R02-000001` trong payload tổng hợp |

Frame 18 chứa JSON plaintext với `device_id=machine-01`, `temperature_c=40.86` và `vibration_mm_s=2.0`. `packet-index.json` cũng ghi 2 CONNECT, 2 CONNACK, 1 SUBSCRIBE, 1 SUBACK, 120 PUBLISH và 120 PUBACK: mỗi telemetry được thấy theo cả hai chiều sensor→broker và broker→subscriber. Đây là số lượng quan sát trong run này, không phải giả thuyết chung.

Quy trình kiểm chứng:

1. Chọn một `run_id` có `manifest.json` trạng thái `complete` và `packet-index.json` có đủ năm mục `first_frames`.
2. Mở `baseline.pcap` trong Wireshark, đi tới từng frame trong index và lưu ảnh minh chứng nếu cần cho báo cáo.
3. Với PCAP lịch sử, đối chiếu `message_id` trong payload PUBLISH với `sensor.jsonl`/`subscriber.jsonl` của cùng run. Với baseline firmware mới, đối chiếu payload với `subscriber.jsonl` và thời gian trong manifest.
4. Ghi lại Client ID, topic và một giá trị payload quan sát được; đây là bằng chứng về khả năng quan sát MQTT plaintext trong **lab dùng credential giả**, chưa phải kết luận cho mọi triển khai MQTT.

**Giới hạn diễn giải:** SUBACK không tự chứng minh quyền đọc của một client khác. Trong kiểm thử cấu hình, broker vẫn trả SUBACK cho một yêu cầu subscribe ngoài ACL của test client; vì vậy quyết định quyền được kiểm chứng bằng một PUBLISH ngoài ACL và dòng `Denied PUBLISH` trong broker log. PCAP E00 chỉ chứa traffic hợp lệ.
