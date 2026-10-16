# Phase 1 — Nhật ký triển khai

> Cập nhật sau đó: simulator sensor đã được gỡ để chuyển sang ESP32. Các E00-R02/R03 bên dưới là kết quả lịch sử; E00 mới chạy bằng `./run.sh` và cần ESP32 thật cùng `.env.firmware` đã cấu hình. `lab_clients/` chỉ chứa subscriber ghi nhận và test client auth/ACL, không tự phát telemetry baseline.

## Trạng thái

- **Hoàn thành ngày 16/10/2026.** Phạm vi: Tuần 1 trong `docs/plan.md` (MQTT 3.1.1 plaintext và baseline E00).
- Gate W1 đạt: hai PCAP baseline lặp lại được; tài liệu `docs/protocol-analysis.md` giải thích 5 loại MQTT control packet bằng số frame thực tế.

## Mốc 1 — Môi trường

- [x] Xác nhận Debian 13 WSL2, Python 3.13.5 và repo dùng `docs/plan.md`; giữ nguyên việc chuyển tài liệu của người dùng.
- [x] Bật WSL Integration cho `Debian` trong Docker Desktop bằng `IntegratedWslDistros: ["Debian"]`, khởi động lại Docker Desktop và xác nhận Docker Engine 29.8.0, Compose v5.5.1 hoạt động.
- [x] Sao lưu cấu hình Windows trước khi đổi tại `%APPDATA%\Docker\settings-store.json.bak-codex-phase1-20261016`.
- Ghi chú: phiên terminal đang mở từ trước khi integration có hiệu lực chưa nhận nhóm `docker`; dùng `sg docker -c '...'` trong phiên đó, hoặc mở terminal Debian mới.

## Mốc 2 — Broker, mạng và client

- [x] `compose.yaml` có broker, sensor, subscriber, test client và capture; mạng `internal: true`, broker không publish port. `docker compose config --quiet` hợp lệ; cấu hình JSON xác nhận 5 service, `internal=True`, `broker_ports=None`.
- [x] Mosquitto 2.1.2 dùng password-file và ACL-file plugin. `.env` chứa credential giả, password file đã băm và bản ACL runtime ở `config/mosquitto/auth/` có owner uid 1883, mode 600; Git và Docker build context đều loại trừ dữ liệu này.
- [x] `python3 scripts/verify_lab.py` chạy thành công: test client hợp lệ được nhận; anonymous và mật khẩu sai bị từ chối; broker log ghi `Denied PUBLISH` cho test client ngoài ACL.
- Phát hiện khi kiểm thử: Mosquitto vẫn trả SUBACK cho một subscription ngoài ACL trong MQTT 3.1.1. Kiểm chứng quyền bằng quyết định từ chối PUBLISH trong broker log, không dùng SUBACK để kết luận quyền đọc của test client.

## Mốc 3 — Baseline E00

- [x] Runner phát 60 bản tin tổng hợp trong 60 giây (1 bản tin/giây, QoS 1, seed 2026), capture trong network namespace của broker, rồi lưu PCAP, log, JSONL và manifest UTC cho mỗi `run_id`.
- [x] **E00-R02:** `status=complete`, gửi 60/60, nhận 60/60, PCAP 55.112 byte. Frame đầu tiên: CONNECT 4, CONNACK 6, SUBSCRIBE 8, SUBACK 9, PUBLISH 18.
- [x] **E00-R03:** `status=complete`, gửi 60/60, nhận 60/60, PCAP 55.030 byte. Cả năm loại packet cũng có trong `packet-index.json`.
- Bằng chứng cục bộ: `data/raw/E00-R02/` và `data/raw/E00-R03/` (bị Git bỏ qua vì PCAP chứa credential giả ở dạng plaintext).
- Lần E00-R01 ban đầu thất bại trước khi phát traffic: `tcpdump` không có quyền ghi thư mục artifact khi container chỉ có `NET_RAW`. Đã thêm `DAC_OVERRIDE`, kiểm chứng capture trực tiếp, và giữ manifest lỗi để đối chiếu. Hai run kế tiếp hoàn thành.

## Mốc 4 — Tài liệu và nghiệm thu

- [x] README hướng dẫn khởi tạo, kiểm chứng broker và chạy lại hai E00 bằng `run_id` duy nhất.
- [x] Thêm `./run.sh` làm entrypoint một lệnh: khởi tạo credential, kiểm tra auth/ACL, chạy một E00 và tạo packet index.
- [x] `docs/protocol-analysis.md` ghi số frame, topic, QoS và payload mẫu dựa trên PCAP E00-R02 thực tế.
- [x] Kiểm tra khi hoàn tất Phase 1: `python3 scripts/init_lab.py` (chạy lặp an toàn), `python3 scripts/verify_lab.py`, `docker compose config --quiet`, `python3 -m compileall -q scripts simulator`, `git diff --check`, và manifest/packet index của hai run simulator-era.

## Bước tiếp theo

Phase 2 theo `docs/plan.md`: listener TLS, E01–E04 và các run có nhãn. Giữ riêng PCAP/log thô và rà soát trước khi chia sẻ.
