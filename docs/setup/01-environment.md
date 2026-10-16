# 1. Môi trường và Docker

## Yêu cầu

- Debian Linux; trên Windows dùng Docker Desktop với Linux containers và WSL Integration bật cho Debian.
- Docker Engine/CLI và Docker Compose v2 trở lên.
- Python 3.10+.
- Repository được clone/mở tại thư mục `mqtt-lab`.

Kiểm tra lệnh:

```bash
docker version
docker compose version
python3 --version
```

Nếu Docker Desktop vừa bật WSL Integration, mở terminal Debian mới trước khi kiểm tra.

## Chuẩn bị credential và ACL

Tại thư mục gốc dự án:

```bash
python3 scripts/init_lab.py
```

Lệnh tạo `.env` chứa credential giả, hash password cho Mosquitto và ACL runtime trong `config/mosquitto/auth/`. Các file runtime và dữ liệu nhạy cảm đã được loại khỏi Git. Nếu đổi ACL nguồn, chạy lại lệnh trên để sinh cấu hình runtime tương ứng.

Không dùng mật khẩu thật. MQTT mặc định là plaintext; PCAP có thể chứa username, password lab và payload.

## Kiểm tra cấu hình

```bash
docker compose config --quiet
python3 scripts/verify_lab.py
```

Script kiểm tra mạng nội bộ, không publish cổng broker mặc định, kiểm tra đăng nhập và các quyền ACL. Xem cấu hình broker tại [02 — Broker](02-broker.md).
