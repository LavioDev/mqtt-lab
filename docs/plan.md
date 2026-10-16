# MQTT LAB — Kế hoạch bài lab An ninh mạng

> **Tên đề tài:** MQTT LAB — Phân tích lưu lượng và phát hiện hành vi bất thường trong mạng MQTT của hệ thống IoT công nghiệp  
> **Tên tiếng Anh:** *MQTT LAB: Network Forensics and Intrusion Detection for Industrial IoT MQTT Traffic*  
> **Loại:** Lab thực nghiệm + mini research project  
> **Trạng thái:** Planning  
> **Phiên bản kế hoạch:** 1.0 — 16/10/2026  
> **Thời gian dự kiến:** 4 tuần; có thể rút xuống 2 tuần theo phạm vi MVP

---

## 1. Mục tiêu

Xây dựng một môi trường MQTT **được kiểm soát và cô lập**, mô phỏng truyền dữ liệu cảm biến công nghiệp, sử dụng Wireshark/tcpdump để phân tích gói tin và triển khai một bộ phát hiện dấu hiệu bất thường (IDS) có thể đánh giá định lượng.

Kết thúc bài lab, phải **chứng minh bằng PCAP + log + số liệu**, không chỉ mô tả lý thuyết:

1. MQTT qua TCP không mã hóa bộc lộ những thông tin gì trên đường truyền.
2. Những dấu hiệu nào phân biệt lưu lượng bình thường với thử nghiệm xác thực sai, truy cập topic trái quyền và tăng tần suất publish bất thường.
3. Cơ chế phát hiện dựa trên quy tắc hoạt động tốt đến đâu, có báo động nhầm trong tình huống bình thường không.
4. Khi bật TLS, khả năng quan sát và phát hiện từ **một cảm biến mạng thụ động** thay đổi như thế nào.

**Đầu ra cuối cùng:** repo có thể chạy lại, PCAP và log thực nghiệm, bảng kết quả đo lường, biểu đồ, báo cáo kỹ thuật và demo ngắn.

## 2. Câu hỏi nghiên cứu và giả thuyết

| ID | Câu hỏi nghiên cứu | Giả thuyết cần kiểm chứng |
|---|---|---|
| RQ1 | Có thể suy ra những thông tin nhạy cảm nào từ MQTT plaintext? | Topic, Client ID, nội dung bản tin và thông tin xác thực MQTT có thể lộ khi dùng TCP không mã hóa (nếu các trường đó được gửi). |
| RQ2 | Những hành vi bất thường trong MQTT có tạo ra dấu hiệu đo được ở mức mạng? | Tần suất CONNECT/PUBLISH, tỷ lệ kết nối thất bại và các mẫu truy cập có thể tạo ra đặc trưng phát hiện được. |
| RQ3 | Bộ phát hiện rule-based có phân biệt được sự cố bình thường và hành vi bất thường không? | Một tập quy tắc có ngưỡng thiết lập từ baseline sẽ phát hiện được một số kịch bản, nhưng có false positive khi thiết bị reconnect/burst hợp lệ. |
| RQ4 | TLS ảnh hưởng thế nào đến phân tích và phát hiện ở điểm giám sát thụ động? | TLS che nội dung MQTT; metadata TCP/TLS vẫn có ích với một số hành vi lưu lượng nhưng không đủ để kết luận mọi kiểu vi phạm. |

Không được viết giả thuyết thành kết luận trước khi có số liệu.

## 3. Phạm vi

### 3.1. MVP — bắt buộc

- MQTT 3.1.1, Mosquitto, một thiết bị giả lập, một subscriber và một client kiểm thử riêng.
- Hai cấu hình broker đối chứng: MQTT/TCP plaintext (`1883`) và MQTT/TLS (`8883`) trong lab.
- Bắt và phân tích PCAP với Wireshark/tcpdump.
- **Bốn kịch bản:** baseline, xác thực thất bại lặp lại có giới hạn, truy cập topic không được phép, publish burst có giới hạn.
- Một detector rule-based viết bằng Python **hoặc** Suricata (chọn một làm lõi để tránh dàn trải).
- Đánh giá Precision, Recall, F1, False Positive Rate theo từng kịch bản; trình bày confusion matrix.
- Một báo cáo và một demo có thể lặp lại.

### 3.2. Nâng cao — chỉ thực hiện sau MVP

- Dùng Zeek để xuất log MQTT 3.1.1 và đối chiếu với Wireshark/broker log.
- Thêm client ID collision/reconnect bất thường dưới kiểm soát.
- Phân tích TLS metadata theo cửa sổ thời gian; so sánh với detector dùng MQTT plaintext.
- So sánh rule-based với Isolation Forest (chỉ khi đã có tập dữ liệu đủ tốt).
- Dashboard Streamlit cho biểu đồ và timeline sự kiện.

### 3.3. Ngoài phạm vi

- Tấn công broker/thiết bị trên Internet hay mạng không thuộc quyền quản lý.
- Khai thác lỗ hổng phần mềm, đánh cắp thông tin thật, chiếm quyền thiết bị.
- Thử nghiệm DDoS quy mô lớn, gây cạn kiệt tài nguyên máy chủ.
- Xây SOC hoàn chỉnh hoặc triển khai production.
- Xây lại MQTT broker; tích hợp toàn bộ LiteBoard không bắt buộc.

## 4. Kiến trúc lab

```text
                LAB NETWORK — ISOLATED / NO PUBLIC EXPOSURE

  Sensor Simulator ───┐
  (Python/ESP32)      │
                      ├──> Mosquitto Broker ───> Legitimate Subscriber
  Test Client ────────┘       | 1883 / 8883           (Python)
 (controlled tests)           |
                              +── Broker logs / auth & ACL decisions

           ┌────────────────────────────────────────────┐
           │ Network observation point                  │
           │ tcpdump -> .pcap -> Wireshark / tshark      │
           │                  └-> feature extraction    │
           │                       └-> Python detector  │
           └────────────────────────────────────────────┘

                    Experiment manifest + Labels
                    run_id / scenario_id / time
                               |
                               v
                   Metrics + Charts + Report
```

**Lưu ý về quan sát:** Cảm biến PCAP phải đặt tại điểm nhìn thấy lưu lượng giữa client và broker. Với Docker Desktop/WSL2 trên Windows, không mặc định giả định Wireshark trên máy chủ thấy toàn bộ lưu lượng container; xác minh interface phù hợp trước khi làm thí nghiệm. Phương án dễ tái tạo là capture ngay trong network namespace chứa luồng đang cần theo dõi.

**Hai cấp quan sát cần tách bạch:**
- **Network-only:** PCAP của bên giám sát thụ động, không có khóa TLS và không có broker logs.
- **Broker-aware:** thêm broker logs/ACL decisions để phân tích nguyên nhân, xác thực nhãn và kiểm chứng những sự kiện mà PCAP không thể hiện rõ.

Tuyệt đối không tuyên bố network-only phát hiện được truy cập topic trái quyền qua TLS nếu không có bằng chứng hoặc nguồn thông tin bổ sung.

## 5. Công nghệ và lựa chọn kỹ thuật

| Vai trò | Công nghệ | Ghi chú |
|---|---|---|
| Triển khai | Docker Compose + Linux/WSL2 | Cố định image tag/digest để tái lập |
| MQTT Broker | Eclipse Mosquitto 2.1.x | Cấu hình tường minh cho authentication, ACL và TLS; ưu tiên plugin theo tài liệu 2.1 |
| MQTT Client | Python + paho-mqtt | Giả lập nhiều profile, phát sinh traffic có nhãn |
| Packet capture | tcpdump | Lưu từng PCAP độc lập theo `run_id` |
| Packet analysis | Wireshark + tshark | Phân tích thủ công và trích xuất thông tin |
| Detector MVP | Python + pandas | Cửa sổ thời gian, rule-based, xuất JSONL/CSV |
| IDS đối chiếu | Suricata (optional) | Rule MQTT cho traffic plaintext; thử nghiệm theo phiên bản đã pin |
| Traffic metadata | Zeek (optional) | Hỗ trợ cơ bản MQTT 3.1.1; không giả định đầy đủ MQTT 5.0 |
| Visualization | matplotlib / Streamlit | MVP chỉ cần biểu đồ tĩnh |
| Dữ liệu | PCAP + JSONL + CSV | Không bắt buộc database |

**Chọn MQTT 3.1.1 cho vòng thí nghiệm chính** để giảm khác biệt công cụ; MQTT 5.0 là phần mở rộng nếu còn thời gian. Các trường MQTT dùng trong Wireshark phải kiểm tra trên phiên bản Wireshark thực tế.

## 6. Mô hình dữ liệu thí nghiệm

### 6.1. Topic và payload mẫu

```text
factory/line-01/machine-01/telemetry
factory/line-01/machine-01/status
factory/line-01/machine-02/telemetry
```

```json
{
  "message_id": "sample-000001",
  "device_id": "machine-01",
  "temperature_c": 42.5,
  "vibration_mm_s": 2.1,
  "occurred_at": "2026-10-16T08:00:00Z"
}
```

Dùng **credential giả**, `device_id` giả và telemetry tổng hợp. Không xuất PCAP chứa bí mật thật lên repo công khai.

### 6.2. Ground truth

Mỗi run có manifest riêng:

```json
{
  "run_id": "E02-R01",
  "scenario_id": "E02",
  "label": "auth_failure_burst",
  "mqtt_version": "3.1.1",
  "transport": "plaintext",
  "started_at_utc": "2026-10-16T08:00:00Z",
  "ended_at_utc": "2026-10-16T08:05:00Z",
  "expected_events": 20,
  "seed": 2026,
  "notes": "Isolated lab; bounded test rate"
}
```

- `run_id`: duy nhất cho mỗi lần chạy; ít nhất **3 lần độc lập/kịch bản/cấu hình** nếu đủ thời gian.
- Lưu **UTC** cho các mốc thời gian và đồng bộ đồng hồ các container/máy.
- Label dựa trên lịch thử nghiệm và logs xác thực, **không** gán nhãn chỉ vì detector đã cảnh báo.
- Không coi mọi gói trong một run tấn công là gói độc hại: khi đánh giá theo cửa sổ thời gian phải đánh dấu đúng khoảng thời gian diễn ra sự kiện.

## 7. Ma trận thí nghiệm

| ID | Kịch bản | Thiết lập | Dấu hiệu cần soi | Minh chứng bắt buộc |
|---|---|---|---|---|
| E00 | Baseline | 1–5 client hợp lệ, telemetry đều, có reconnect/burst hợp lệ | CONNECT, CONNACK, PUBLISH, độ trễ, packet rate | PCAP + normal logs + baseline chart |
| E01 | Plaintext vs TLS | Gửi cùng thông điệp trên 1883 và 8883 | Trường MQTT quan sát được vs metadata TLS | Ảnh Wireshark + bảng visibility |
| E02 | Repeated auth failures | Một client lab thử số lần đăng nhập sai **có giới hạn** | Kết nối ngắn, retry rate, CONNACK thất bại (nếu nhìn được) | PCAP + auth logs + alert |
| E03 | Unauthorized topic access | Client dùng quyền bị giới hạn thử SUBSCRIBE/PUBLISH ngoài ACL | MQTT SUBSCRIBE/SUBACK hoặc broker ACL decision | PCAP + ACL logs + kết luận khả năng nhận biết |
| E04 | Controlled publish burst | Client lab tăng gửi từ baseline lên mức giới hạn đã định | messages/s, bytes/s, burst duration | PCAP + time-series + alert |

**Biến kiểm soát:** cùng broker version, máy chủ, số lượng client, cấu hình QoS, kích thước payload, thời lượng đo và nền mạng khi so sánh (trừ biến chủ đích thay đổi). Đừng thay đổi nhiều biến cùng lúc.

**Nhịp thử nghiệm gợi ý (có thể điều chỉnh để tránh quá tải):** baseline 1 msg/s/thiết bị; burst 5–20 msg/s từ một client giả lập trong 20–30 giây; thử xác thực sai tối đa vài chục lần ở tốc độ thấp. Đây là profile lab, **không phải ngưỡng tấn công tiêu chuẩn**.

### 7.1. Điều cần phân tích trong Wireshark

- TCP handshake, đóng kết nối và kết nối ngắn bất thường.
- MQTT `CONNECT`/`CONNACK`: client ID, protocol version, trạng thái chấp nhận/từ chối.
- `PUBLISH`: topic, QoS, DUP flag, message identifier (nếu có), kích thước payload.
- `SUBSCRIBE`/`SUBACK`: yêu cầu subscription và kết quả; đối chiếu broker logs để kết luận quyền thực tế.
- `PINGREQ`/`PINGRESP`, `DISCONNECT` và reconnect pattern.
- TLS handshake và encrypted application data (không giả định giải mã được MQTT khi không có key).

Bộ lọc khởi đầu (xác minh theo bản Wireshark cài đặt):

```text
mqtt
mqtt.msgtype == 1             # CONNECT
mqtt.msgtype == 3             # PUBLISH
tcp.port == 1883
tcp.port == 8883
tls
```

## 8. Thiết kế phát hiện (IDS)

### 8.1. Feature extraction

Gộp traffic theo `source IP/client (nếu nhìn thấy)` và cửa sổ thời gian **10 giây**; kiểm tra độ nhạy với cửa sổ 5 và 30 giây.

| Feature | Ý nghĩa | Nguồn |
|---|---|---|
| `connection_count` | Số kết nối TCP mới | PCAP, cả TCP/TLS |
| `connection_duration_ms` | Thời lượng session | PCAP |
| `bytes_in`, `bytes_out` | Lưu lượng hai chiều | PCAP |
| `packets_per_sec` | Tốc độ gói tin | PCAP |
| `publish_per_sec` | Tốc độ MQTT PUBLISH | MQTT plaintext / broker-aware |
| `connack_failures` | Số CONNACK báo lỗi | MQTT plaintext / broker-aware |
| `acl_denials` | Số truy cập bị từ chối | Broker logs, **không phải TLS PCAP thụ động** |
| `inter_arrival_time_ms` | Khoảng cách gói | PCAP |
| `avg_packet_size` | Kích thước gói trung bình | PCAP |

### 8.2. Quy tắc MVP

- **R1 — Reconnection anomaly:** số kết nối mới/cửa sổ vượt ngưỡng baseline.
- **R2 — Authentication failure anomaly:** số CONNACK thất bại hoặc auth-denied log vượt ngưỡng; không áp dụng trực tiếp với TLS PCAP thụ động.
- **R3 — Unauthorized access attempt:** có ACL-denied event ở broker; phân loại đây là **broker-assisted detection**.
- **R4 — Publish rate anomaly:** PUBLISH/s vượt baseline; nếu TLS network-only thì chỉ dùng đặc trưng lưu lượng thay thế, không khẳng định đếm được PUBLISH.

**Hiệu chỉnh ngưỡng:** dùng các run bình thường dành riêng cho tuning (ví dụ percentile 99 hoặc `median + k*MAD`, tùy phân phối); sau đó **khóa ngưỡng** và đánh giá bằng các run độc lập. Không chọn ngưỡng dựa trên toàn bộ dữ liệu test.

### 8.3. Hai nhánh detector để so sánh công bằng

1. **Plaintext application-aware:** dùng MQTT header + network features; có thể thử Suricata rules.
2. **TLS network-only:** chỉ dùng TCP/TLS metadata; *không* dùng MQTT plaintext fields, broker logs hay khóa TLS trong lúc suy luận.

**Đối chứng quan trọng:** chạy thêm metadata-only trên traffic plaintext để phân biệt hiệu ứng do **mất khả năng quan sát** với hiệu ứng do thay đổi bản thân traffic khi dùng TLS.

## 9. Đánh giá khoa học

### 9.1. Các chỉ số

- **TP:** cửa sổ bất thường được phát hiện đúng.
- **FP:** cửa sổ bình thường bị cảnh báo nhầm.
- **FN:** cửa sổ bất thường bị bỏ sót.
- **TN:** cửa sổ bình thường không bị cảnh báo.

```text
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 * Precision * Recall / (Precision + Recall)
FPR       = FP / (FP + TN)
```

Quy ước xử lý mẫu số bằng 0 (trả N/A thay vì bịa 100%). Báo cáo confusion matrix và **false alarms/hour** vì dataset có thể mất cân bằng. Nếu sự kiện ngắn nhưng bao qua hai cửa sổ, ghi rõ quy tắc gán nhãn.

### 9.2. Quy trình đánh giá

1. Thu các run bình thường cho baseline/tuning.
2. Chạy các kịch bản bất thường ở mức thử nghiệm cho phép và các normal hard cases (ví dụ reconnect do restart hợp lệ).
3. Tách **theo run**, không random từng packet/window vì dễ rò rỉ dữ liệu cùng phiên.
4. Tính chỉ số **theo kịch bản và tổng thể**, không chỉ Accuracy.
5. So sánh kết quả giữa `plaintext full features`, `plaintext metadata-only`, `TLS metadata-only`.
6. Lặp lại run; báo cáo độ dao động/giá trị trung bình, không chọn một lần đẹp nhất.

### 9.3. Biểu đồ bắt buộc

- Timeline các giai đoạn bình thường và giai đoạn thử nghiệm bất thường.
- MQTT/TCP connection rate và publish rate (nếu quan sát được).
- Confusion matrix / Precision–Recall–F1 theo kịch bản.
- So sánh feature visibility và hiệu năng detector plaintext vs TLS.
- Ít nhất một ví dụ **false positive** được giải thích bằng PCAP/log.

## 10. Kế hoạch thực hiện theo tuần

### Tuần 1 — Thiết lập nền tảng và hiểu giao thức

- [ ] Tạo repo, Docker Compose và mạng lab cô lập.
- [ ] Cấu hình Mosquitto plaintext với credential giả, ACL cố ý giới hạn.
- [ ] Tạo Python sensor simulator, subscriber và test client.
- [ ] Bắt PCAP baseline; xác nhận capture nhìn thấy đúng luồng client↔broker.
- [ ] Phân tích CONNECT, CONNACK, PUBLISH, SUBSCRIBE bằng Wireshark.
- [ ] Ghi lại version, lệnh chạy, cấu hình và ảnh minh chứng.

**Gate W1:** Có baseline PCAP tái lập được và giải thích được ít nhất 5 MQTT control packet.

### Tuần 2 — Thí nghiệm an ninh mạng

- [ ] Thiết lập TLS listener cho broker, dùng CA/cert thử nghiệm nội bộ.
- [ ] Thực hiện E01 (plaintext vs TLS) và lập bảng dữ liệu quan sát được.
- [ ] Thực hiện E02 (auth failure), E03 (ACL deny), E04 (controlled publish burst).
- [ ] Thu PCAP + broker logs + manifest/label cho từng run.
- [ ] Bổ sung normal hard cases để thử false positive.
- [ ] Kiểm tra dữ liệu không chứa thông tin nhạy cảm thật trước khi chia sẻ.

**Gate W2:** Có đủ 5 loại run E00–E04, có nhãn thời gian rõ và không vi phạm giới hạn lab.

### Tuần 3 — IDS và đánh giá

- [ ] Viết parser/feature extractor từ PCAP hoặc logs xuất bởi tshark.
- [ ] Triển khai R1–R4; phân biệt network-only và broker-assisted.
- [ ] Chia data tuning/test theo run và khóa ngưỡng.
- [ ] Xuất alert JSONL: `timestamp`, `run_id`, `rule_id`, `entity`, `score`, `evidence`.
- [ ] Tính confusion matrix, Precision, Recall, F1, FPR, false alarms/hour.
- [ ] Phân tích tối thiểu 2 false positive/false negative nếu xuất hiện.

**Gate W3:** Detector chạy lại được trên dataset và tự sinh file metrics.

### Tuần 4 — So sánh, báo cáo và demo

- [ ] So sánh plaintext app-aware với metadata-only và TLS metadata-only.
- [ ] Tạo biểu đồ, chọn PCAP minh họa tốt nhất, giải thích giới hạn.
- [ ] Viết báo cáo 6–10 trang hoặc theo yêu cầu giảng viên.
- [ ] Tạo demo 5–8 phút: traffic bình thường → scenario → PCAP → alert → kết quả.
- [ ] Hoàn thiện README, setup, hướng dẫn reproduce, tài liệu ethical scope.

**Gate W4:** Người khác có thể chạy lại 1 scenario và tái tạo được ít nhất 1 cảnh báo cùng biểu đồ tương ứng.

### Nếu chỉ có 2 tuần

Ưu tiên **E00 + E01 + E02 + E04**, Python rule-based, tối đa 3–4 biểu đồ. Giữ E03 làm phần mở rộng nếu hệ thống ACL mất nhiều thời gian debug. Không thêm ML, Zeek và dashboard trước khi MVP xong.

## 11. Cấu trúc repo dự kiến

```text
mqtt-lab/
├── README.md
├── plan.md
├── compose.yaml
├── .env.example
├── config/
│   └── mosquitto/
│       ├── mosquitto.conf
│       ├── acl.conf
│       └── tls/                 # chỉ public cert mẫu; không commit private keys
├── simulator/
│   ├── sensor.py
│   ├── subscriber.py
│   └── scenarios.py
├── capture/
│   ├── capture.sh
│   └── export_features.sh
├── detector/
│   ├── features.py
│   ├── rules.py
│   └── evaluate.py
├── experiments/
│   ├── scenarios.yaml
│   └── manifests/
├── data/
│   ├── raw/                 # PCAP/log có thể lớn, không commit mặc định
│   ├── processed/
│   └── labels/
├── reports/
│   ├── figures/
│   └── report.md
└── docs/
    ├── threat-model.md
    ├── protocol-analysis.md
    ├── experiment-methodology.md
    └── ethics-and-scope.md
```

**Git hygiene:** `.gitignore` phải loại trừ `.env`, private keys, credential files, các PCAP nhạy cảm và dữ liệu quá lớn. Nếu cần xuất bản dataset, tạo phiên bản đã làm sạch và ghi license/README riêng.

## 12. Tiêu chí nghiệm thu

| Mục | Điều kiện đạt |
|---|---|
| Reproducibility | `docker compose up` dựng được môi trường; có hướng dẫn chạy ít nhất 1 scenario |
| Protocol understanding | Phân tích PCAP minh họa ≥5 MQTT control packet |
| Security evidence | Đối chiếu được plaintext/TLS và ≥2 hành vi bất thường bằng PCAP/log |
| Detection | Có ≥3 rule hoạt động, sinh alert giải thích được |
| Evaluation | Có confusion matrix và Precision/Recall/F1/FPR theo kịch bản |
| Scientific rigor | Có baseline, ground truth, test split theo run, ít nhất 1 false positive analysis |
| Report | Giải thích kết quả, giới hạn quan sát, rủi ro bảo mật và cách giảm thiểu |
| Safety | Mọi hoạt động chỉ trên tài nguyên tự kiểm soát, trong mạng lab cô lập |

**Định nghĩa “outstanding” (stretch goal):** thêm so sánh 3 cấu hình feature (plaintext đầy đủ, plaintext metadata-only, TLS metadata-only), lặp lại các run và trình bày vì sao một số hành vi không thể suy ra từ PCAP thuần túy sau khi mã hóa.

## 13. Rủi ro và cách xử lý

| Rủi ro | Xử lý |
|---|---|
| Không thấy traffic Docker trên Wireshark Windows | Capture trong đúng network namespace; xác minh PCAP baseline trước |
| Quá nhiều tool, thiếu thời gian | Chỉ giữ Wireshark + Mosquitto + Python; Suricata/Zeek là tùy chọn |
| Zeek không phân tích hết MQTT 5 | Chốt MQTT 3.1.1 cho MVP; không giả định compatibility |
| ACL bị từ chối nhưng PCAP không phản ánh rõ | Dùng broker logs làm ground truth, công bố giới hạn network-only |
| TLS che MQTT fields | Chạy hai detector với nguồn feature tách biệt; không dùng khóa TLS để suy luận network-only |
| Alert giả do burst/reconnect bình thường | Thu hard-negative cases, hiệu chỉnh từ baseline và báo cáo false positive |
| Dataset nhỏ hoặc thiên lệch | Thu nhiều run, thay seed, chia theo run, không tuyên bố mô hình tổng quát hóa ra Internet |
| Test làm ảnh hưởng mạng ngoài | Private lab network, không expose broker, giới hạn rate/duration/concurrency |

## 14. Nguyên tắc an toàn và đạo đức

- Chỉ thực hành với broker, client, mạng và tài khoản do nhóm sở hữu hoặc có ủy quyền rõ ràng.
- Không thực hiện brute-force vô hạn, flood gây gián đoạn hoặc dò quét mục tiêu bên ngoài lab.
- Không dùng mật khẩu thật; không đăng tài liệu chứa khóa cá nhân TLS.
- Thêm giới hạn cứng cho số lần kết nối, số client, thời gian và lưu lượng thử nghiệm.
- Ghi rõ môi trường, phạm vi và tác động của từng kịch bản trong báo cáo.
- Chỉ công bố PCAP/log sau khi rà soát dữ liệu nhạy cảm.

## 15. Dàn ý báo cáo và demo

1. **Introduction:** bài toán bảo mật MQTT trong Industrial IoT, phạm vi và động lực.
2. **Background:** MQTT 3.1.1, luồng packet, plaintext/TLS, auth/ACL.
3. **Threat model & methodology:** tài sản, giả định, network topology, kịch bản, nhãn.
4. **Traffic analysis:** PCAP bằng chứng, đối chiếu giữa các điều kiện.
5. **IDS design:** features, rules, ngưỡng và khả năng giải thích.
6. **Results:** confusion matrix, F1/FPR, biểu đồ và so sánh TLS.
7. **Discussion:** false positives, giới hạn quan sát, hạn chế dataset, hướng cải thiện.
8. **Conclusion:** trả lời từng câu hỏi nghiên cứu bằng kết quả đo.

**Flow demo:** mở baseline PCAP → soi MQTT CONNECT/PUBLISH → chuyển sang thử nghiệm có giới hạn → mở PCAP/log đối chiếu → xem alert → trình bày bảng Precision/Recall và một false positive → bật TLS để minh họa sự khác nhau về visibility.

## 16. Tài liệu chính thức tham khảo

- MQTT v3.1.1 — OASIS: https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html
- Wireshark MQTT display filters: https://www.wireshark.org/docs/dfref/m/mqtt.html
- Mosquitto configuration: https://mosquitto.org/man/mosquitto-conf-5.html
- Mosquitto 2.1 listener authentication/ACL migration: https://www.mosquitto.org/documentation/listeners/per-listener-settings/
- Mosquitto ACL file plugin: https://www.mosquitto.org/documentation/plugins/acl-file/
- Suricata MQTT rule keywords: https://docs.suricata.io/en/latest/rules/mqtt-keywords.html
- Zeek MQTT analyzer (scope v3.1.1): https://docs.zeek.org/en/v8.0.4/scripts/base/protocols/mqtt/main.zeek.html

---

> **Ưu tiên triển khai:** Bắt được một PCAP sạch + phân tích đúng giao thức + có ground truth trước; tiếp theo mới dựng detector. Không đánh đổi tính kiểm chứng để lấy dashboard đẹp hoặc thêm AI cho có.
