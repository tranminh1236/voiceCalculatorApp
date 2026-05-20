# VoiceApp — Handwritten Number Recognition with Audio Supervision

**Date:** 2026-04-30
**Status:** Draft for review
**Scope:** MVP (Phase A) — data collection + manual correction + audio↔OCR matching. Training pipeline (Phase B) is deferred until ~200–500 captures are collected.

---

## 1. Mục tiêu

Xây dựng PWA cá nhân giúp:

1. Chụp ảnh ghi chú viết tay chứa nhiều con số rời rạc.
2. OCR các con số trong ảnh (kèm bounding box).
3. Ghi âm tiếng Việt đọc các con số cần cộng cho từng nhóm (group).
4. Tự động ghép cặp số trong audio ↔ số trong ảnh để xác định "số nào trong ảnh thuộc nhóm nào".
5. Tính tổng có trọng số: `final = Σ (sum_group_i × multiplier_group_i)` với hệ số nhân gắn theo template.
6. Cho phép sửa tay các số OCR sai trước khi finalize.
7. Lưu trữ data (image, audio, OCR result, corrections, matches, final value) để sau này train model auto-classify "số nào thuộc nhóm nào" dựa vào layout.

**Phi mục tiêu (cho Phase A):** training/auto-classification, multi-user, cloud deployment, mobile native, real-time streaming STT.

---

## 2. Use case ví dụ

Hình viết tay layout `2x3`:
```
a - b - c
e - d - f
```
- Group 1: `a + e + c + f`, multiplier = 80
- Group 2: `2a + 2c` (mỗi số đếm 2 lần), multiplier = 82
- Group 3: trên hình khác layout `a-b / e-d`: `b + d`, multiplier = 14.5

`final = (a+e+c+f) × 80 + (2a+2c) × 82 + (b+d) × 14.5`

Mỗi loại layout = 1 **Template** với danh sách multipliers gắn vào group index.

---

## 3. Kiến trúc

```
┌──────────────────────────┐         HTTP / multipart        ┌──────────────────────────┐
│  PWA Frontend (browser)  │ ◄─────────────────────────────► │  FastAPI Backend (local) │
│  React + TS + Vite       │                                 │  Python 3.11+            │
│  - Camera capture        │                                 │  - Whisper (STT, vi)     │
│  - MediaRecorder (audio) │                                 │  - PaddleOCR             │
│  - Annotation overlay    │                                 │  - VN number parser      │
│  - PWA install / offline │                                 │  - Match engine          │
└──────────────────────────┘                                 │  - SQLite + filesystem   │
                                                             └──────────────────────────┘
                                                                          │
                                                                          ▼
                                                             ┌──────────────────────────┐
                                                             │  Training scripts        │
                                                             │  (Phase B, on demand)    │
                                                             └──────────────────────────┘
```

**Triển khai:** user chạy `uvicorn` backend localhost:8000, mở PWA tại localhost:5173 (dev) hoặc build static + serve qua FastAPI ở production-local.

---

## 4. Domain model

| Entity | Các trường chính | Ghi chú |
|---|---|---|
| `Template` | id, name, **groups** (list[GroupDef]), created_at | Mỗi `GroupDef = { index, label, bet_type, multiplier, default_provinces }`. `bet_type` ∈ `lo` / `de` / `xien_2` / `xien_3` / `xien_4` / `3cang` / `xien_quay`. `default_provinces` là gợi ý mặc định khi tạo capture (vd: `["HN"]` cho group lô đài Hà Nội); user override được tại từng capture |
| `Capture` | id, template_id, image_path, final_value, status, created_at, **group_provinces** (dict[group_index → list[province_code]]), **metadata**: writer_name, note_date, tags[], notes | **Quan trọng**: provinces được set per-group, không phải toàn capture. Đa số group thường chỉ 1 đài (vd HN); một số group có thể đặt nhiều đài (vd DNG+KH). Stake hiệu dụng cho 1 số trong group g = `stake(n) × len(group_provinces[g])` |
| `Province` | code (vd `HN`, `DNG`, `KH`), region (`mb`/`mt`/`mn`), name | Lookup table tĩnh; seed sẵn 3 miền |
| `LotteryDraw` | id, province_code, draw_date, source_image_path, prizes_json, tails_2d_json (multiset 18-27 số đuôi-2 tuỳ region), special_tail_2d | 1 đài × 1 ngày = 1 draw. UNIQUE(province_code, draw_date). Ảnh KQ có thể chứa nhiều đài → tạo nhiều LotteryDraw. MB: 27 đuôi; MT/MN: 18 đuôi/đài |
| `CaptureResult` | id, capture_id, hits_json (per province × per group × per number breakdown), total_stake, winning_total_payout, profit_loss, settled_at | Settle bằng cách join với tất cả LotteryDraw tương ứng `(province ∈ capture.provinces, draw_date)`. UNIQUE per capture |
| `OcrNumber` | id, capture_id, bbox (x,y,w,h), raw_text, raw_value, corrected_value (nullable), confidence | Mỗi số OCR detect được. `effective_value = corrected_value ?? raw_value` |
| `AudioGroup` | id, capture_id, group_index, audio_path, transcript, parsed_numbers (list[float]), sum, multiplier_snapshot | 1 lần ghi âm = 1 sub-total. `multiplier_snapshot` copy từ template tại thời điểm ghi để bất biến lịch sử |
| `Match` | id, ocr_number_id, audio_group_id, confidence, source (`auto`/`manual`) | Một OCR number có thể match 0 hoặc nhiều audio_group (nếu group dùng số đó nhiều lần — vd "2a") |

---

## 5. User flow chi tiết (1 capture)

1. **Chọn template** (hoặc tạo mới: name + list multipliers).
2. **Chụp ảnh** → `POST /api/captures` (multipart: image + template_id). Backend:
   - Lưu image vào `data/media/captures/{capture_id}.jpg`
   - Chạy PaddleOCR → trích xuất các vùng có chữ → filter chỉ giữ vùng chứa số (regex `^-?\d+([.,]\d+)?$` hoặc fuzzy)
   - Tạo `OcrNumber` records với bbox + raw_value + confidence
   - Trả về Capture object với danh sách OcrNumber
3. **UI hiển thị ảnh + overlay bbox** với giá trị OCR. User:
   - Tick vào số bị sai → nhập giá trị đúng → `POST /api/captures/{id}/correct` { ocr_number_id, corrected_value }
   - Có thể "thêm số bị OCR bỏ sót" bằng cách click vẽ bbox tay (optional, nice-to-have)
4. **Ghi âm group 1**: bấm record → đọc "23 cộng 5 cộng 12 cộng 18 bằng" → bấm stop → upload `POST /api/captures/{id}/audio` { group_index, audio_blob }. Backend:
   - Lưu audio `data/media/audio/{capture_id}_g{idx}.webm`
   - Whisper STT (vi) → transcript
   - VN number parser → parsed_numbers + sum
   - Match engine: với mỗi parsed_number, tìm OcrNumber chưa được match cho group này có `effective_value` gần nhất → tạo Match (auto)
   - Trả về AudioGroup + matches để UI tô màu
5. **Lặp lại cho các group khác** (chú ý: cùng OcrNumber có thể được match cho nhiều group khác nhau, vd với rule "2a" — group đó gọi audio cho `a` 2 lần).
6. **Finalize**: `POST /api/captures/{id}/finalize`. Backend tính `final_value = Σ sum_i × multiplier_i`, set status=`final`, trả về kết quả.
7. **Xem lại** trong History; có thể reopen để chỉnh sửa.

---

## 6. Match engine

**Input:** `audio_group.parsed_numbers[]`, list `OcrNumber` của capture với `effective_value` và `assigned_count` (số lần đã được match).

**Algorithm (heuristic):**
```
# Note: cùng OcrNumber có thể được match nhiều lần trong cùng audio_group
# (vd rule "2a + 2c" → audio đọc số a hai lần). Mỗi lần đọc tạo 1 Match riêng.

for audio_value in parsed_numbers:  # mỗi lần đọc = 1 entry
    candidates = ocr_numbers, rank by:
      1. exact value equality (effective_value == audio_value)
      2. nếu có nhiều ocr cùng value bằng nhau, ưu tiên ocr có total_match_count thấp
         (giảm ambiguity khi ảnh có nhiều số trùng giá trị)
      3. nếu không exact: numeric distance + visually-similar OCR error patterns
         (0/6, 1/7, 3/8) — Levenshtein trên digit string
    if best candidate within threshold (default: chỉ exact-match):
        create Match(ocr=best, group=this, confidence=score, source='auto')
    else:
        ghi nhận unmatched audio entry → UI cho user gán tay
```

**Hệ quả schema:** bảng `matches` không có UNIQUE constraint trên `(ocr_number_id, audio_group_id)` — cho phép nhiều row cho cùng cặp.

**Note cho training (Plan 7):** mỗi `OcrNumber` có thể được derive ra `group_index` (hoặc `null` nếu không match group nào) từ bảng `matches` join qua `audio_groups.group_index`. Đây chính là nhãn (label) để train model auto-classify "số nào thuộc group nào" dựa vào (image crop + bbox + position features).

**UI cho user fix match:** nếu auto-match sai, user có thể click 1 OCR number → chọn group để gán/bỏ gán (`POST /api/matches` manual).

---

## 7. Vietnamese number parser

Yêu cầu: convert chuỗi tiếng Việt như:
```
"hai mươi ba cộng năm cộng mười hai cộng trăm lẻ năm cộng mười tám bằng"
```
→ `parsed_numbers = [23, 5, 12, 105, 18]`, sum = 163.

**Components:**
- Tokenizer: tách theo whitespace, normalize (lowercase, bỏ dấu câu).
- Delimiter set: `["cộng", "+", "và", "với"]` (chính: "cộng").
- Terminator set: `["bằng", "=", "tổng", "kết thúc"]` + silent-end (Whisper trả full transcript, terminator chỉ để tự cắt nếu user nói).
- Number-word parser: hỗ trợ:
  - 0-9: "không/một/hai/ba/bốn/năm/sáu/bảy/tám/chín"
  - 10-99: "mười X", "X mươi", "X mươi Y", "X mươi lăm/tư/mốt"
  - 100-999: "X trăm", "X trăm lẻ Y", "X trăm Y mươi Z"
  - Nghìn/triệu/tỷ
  - "rưỡi" = 0.5, "phẩy" = decimal point, "âm" = negative
  - Variants: "linh"="lẻ", "bốn"="tư", "năm"="lăm", "một"="mốt"
- Output: list of float.

**Test cases:** unit tests phải cover ~30+ biến thể tiếng Việt.

---

## 8. API surface

| Method | Path | Body / Query | Response |
|---|---|---|---|
| POST | `/api/templates` | `{ name, multipliers }` | Template |
| GET | `/api/templates` | — | Template[] |
| PATCH | `/api/templates/{id}` | partial | Template |
| POST | `/api/captures` | multipart: image + template_id | Capture (with ocr_numbers[]) |
| GET | `/api/captures` | pagination | Capture[] (summary) |
| GET | `/api/captures/{id}` | — | Capture full (ocr, audio_groups, matches) |
| PATCH | `/api/captures/{id}/ocr/{ocr_id}` | `{ corrected_value }` | OcrNumber |
| POST | `/api/captures/{id}/audio` | multipart: audio + group_index | AudioGroup + matches[] |
| POST | `/api/captures/{id}/matches` | `{ ocr_number_id, audio_group_id, action: 'add'/'remove' }` | Match |
| POST | `/api/captures/{id}/finalize` | — | Capture (status=final, final_value) |
| PATCH | `/api/captures/{id}/metadata` | partial: writer_name, note_date, tags, notes | Capture |
| GET | `/api/provinces` | — | Province[] (lookup) |
| POST | `/api/lottery-draws/parse` | multipart: image + draw_date + region | { detected_provinces[]: { province_code, prizes, tails_2d, special_tail_2d, bbox } } — preview để user confirm trước khi commit (vì 1 ảnh có nhiều đài) |
| POST | `/api/lottery-draws` | JSON: `{ draws: [{ province_code, draw_date, prizes, source_image_path? }] }` | LotteryDraw[] (commit batch) |
| GET | `/api/lottery-draws` | filter: province_code, date range | LotteryDraw[] |
| GET | `/api/lottery-draws/{id}` | — | LotteryDraw full |
| POST | `/api/captures/{id}/settle` | optional `{ override_group_provinces: { "1": [...] } }` (default = capture.group_provinces) | CaptureResult (server tự tìm các draw matching cho từng group × province ∈ group_provinces[g] tại date = capture.note_date; báo lỗi nếu thiếu draw; tính hit) |
| GET | `/api/captures/{id}/risk` | — | Risk view: per-number payout, lãi/lỗ, recommend pass/take (Plan 8) |
| WS | `/api/stt/stream` | WebSocket: client gửi audio chunk PCM 16k | Server gửi partial transcripts + parsed numbers tích lũy real-time (Plan 9) |

---

## 9. Database schema (SQLite via SQLAlchemy)

```sql
CREATE TABLE templates (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  multipliers_json TEXT NOT NULL,  -- JSON: [80.0, 82.0, 14.5]
  created_at TEXT NOT NULL
);

CREATE TABLE captures (
  id INTEGER PRIMARY KEY,
  template_id INTEGER NOT NULL REFERENCES templates(id),
  image_path TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('draft','final','settled')),
  final_value REAL,
  group_provinces_json TEXT NOT NULL,   -- JSON dict { "1": ["HN"], "2": ["HN"], "3": ["DNG","KH"] }
  -- metadata
  writer_name TEXT,
  note_date TEXT,                 -- YYYY-MM-DD trên ghi chú
  tags_json TEXT,
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE provinces (
  code TEXT PRIMARY KEY,          -- 'HN', 'DNG', 'KH', ...
  region TEXT NOT NULL CHECK (region IN ('mb','mt','mn')),
  name TEXT NOT NULL              -- 'Hà Nội', 'Đà Nẵng', 'Khánh Hòa', ...
);

CREATE TABLE lottery_draws (
  id INTEGER PRIMARY KEY,
  province_code TEXT NOT NULL REFERENCES provinces(code),
  draw_date TEXT NOT NULL,             -- YYYY-MM-DD
  source_image_path TEXT,              -- nullable nếu nhập tay; có thể chia sẻ giữa nhiều draw cùng ảnh
  prizes_json TEXT NOT NULL,           -- { "DB":["86569"], "1":["66320"], ... } cấu trúc theo region
  tails_2d_json TEXT NOT NULL,         -- JSON multiset of int (00-99). MB: 27; MT/MN: 18 per đài
  special_tail_2d INTEGER NOT NULL,    -- đuôi 2 số của ĐB
  UNIQUE(province_code, draw_date)
);

CREATE TABLE capture_results (
  id INTEGER PRIMARY KEY,
  capture_id INTEGER NOT NULL UNIQUE REFERENCES captures(id) ON DELETE CASCADE,
  lottery_draw_id INTEGER NOT NULL REFERENCES lottery_draws(id),
  hits_json TEXT NOT NULL,             -- chi tiết: per group, số nào trong group đó trúng
  total_stake REAL NOT NULL,
  winning_total_payout REAL NOT NULL,
  profit_loss REAL NOT NULL,           -- = winning_total_payout - total_stake
  settled_at TEXT NOT NULL
);

CREATE TABLE ocr_numbers (
  id INTEGER PRIMARY KEY,
  capture_id INTEGER NOT NULL REFERENCES captures(id) ON DELETE CASCADE,
  bbox_x REAL, bbox_y REAL, bbox_w REAL, bbox_h REAL,
  raw_text TEXT,
  raw_value REAL,
  corrected_value REAL,
  confidence REAL
);

CREATE TABLE audio_groups (
  id INTEGER PRIMARY KEY,
  capture_id INTEGER NOT NULL REFERENCES captures(id) ON DELETE CASCADE,
  group_index INTEGER NOT NULL,
  audio_path TEXT NOT NULL,
  transcript TEXT,
  parsed_numbers_json TEXT,
  sum REAL,
  multiplier_snapshot REAL NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE matches (
  id INTEGER PRIMARY KEY,
  ocr_number_id INTEGER NOT NULL REFERENCES ocr_numbers(id) ON DELETE CASCADE,
  audio_group_id INTEGER NOT NULL REFERENCES audio_groups(id) ON DELETE CASCADE,
  confidence REAL,
  source TEXT NOT NULL CHECK (source IN ('auto','manual'))
);
```

---

## 10. Project structure

```
voiceApp/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, CORS, static
│   │   ├── api/
│   │   │   ├── templates.py
│   │   │   ├── captures.py
│   │   │   └── matches.py
│   │   ├── services/
│   │   │   ├── ocr.py              # PaddleOCR wrapper
│   │   │   ├── stt.py              # Whisper wrapper
│   │   │   ├── parser_vn.py        # Vietnamese number parser
│   │   │   └── matcher.py          # Match engine
│   │   ├── models.py               # SQLAlchemy
│   │   ├── schemas.py              # Pydantic
│   │   └── db.py
│   ├── data/
│   │   ├── voiceapp.db             # SQLite
│   │   └── media/
│   │       ├── captures/           # *.jpg
│   │       └── audio/              # *.webm
│   ├── tests/
│   │   ├── test_parser_vn.py       # ưu tiên cao, ~30 cases
│   │   ├── test_matcher.py
│   │   └── test_api.py
│   ├── scripts/
│   │   └── train.py                # Phase B placeholder
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── api/                    # axios client + types
│   │   ├── components/
│   │   │   ├── CameraCapture.tsx
│   │   │   ├── OcrOverlay.tsx      # canvas + bbox overlay
│   │   │   ├── AudioRecorder.tsx
│   │   │   ├── GroupPanel.tsx
│   │   │   └── ResultSummary.tsx
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   ├── NewCapture.tsx
│   │   │   ├── CaptureDetail.tsx
│   │   │   ├── History.tsx
│   │   │   └── Templates.tsx
│   │   ├── hooks/
│   │   │   ├── useRecorder.ts
│   │   │   └── useCamera.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   │   └── manifest.webmanifest
│   ├── vite.config.ts              # vite-plugin-pwa
│   ├── tsconfig.json
│   └── package.json
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-04-30-voiceapp-handwritten-number-recognition-design.md
└── README.md
```

---

## 11. Tech stack chi tiết

**Backend:**
- Python 3.11+
- FastAPI + uvicorn
- SQLAlchemy 2.x + SQLite
- PaddleOCR (`paddlepaddle`, `paddleocr`) — model VI handwriting
- openai-whisper (model `small` or `medium`, language=`vi`)
- Pydantic v2
- pytest

**Frontend:**
- React 18 + TypeScript
- Vite + vite-plugin-pwa
- Axios
- TailwindCSS (chỉnh nhanh UI)
- MediaRecorder API + getUserMedia for camera/mic
- Canvas API for bbox overlay
- Zustand (state nhẹ) — optional

**Dev tooling:**
- ESLint + Prettier (frontend)
- Ruff + Black (backend)
- Pre-commit hook (optional)

---

## 12. Performance / non-functional targets (relaxed cho personal use)

| Metric | Target |
|---|---|
| OCR per image | < 10s trên CPU (PaddleOCR CPU mode chấp nhận được) |
| STT per 10s audio | < 5s (Whisper small CPU) |
| API p95 (non-ML) | < 200ms |
| DB size | < 5 GB sau 1000 captures |
| Browser support | Chromium-based + Safari iOS 15+ |

---

## 13. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Handwriting OCR yếu với chữ cẩu thả | (a) Cho user sửa tay; (b) prompt ảnh sáng + chữ rõ trong UI; (c) Phase B train fine-tune |
| Whisper sai số tiếng Việt ("năm" vs "lăm") | Parser phải tolerant; cho user thấy transcript để verify nhanh |
| Match sai khi có nhiều số giá trị giống nhau | UI cho user fix match thủ công; Match có cờ `source` |
| User quên chụp ảnh trước khi ghi âm | UI ép thứ tự: chỉ enable record khi đã có capture với OCR result |
| SQLite lock khi có nhiều ghi đồng thời | Personal use → single user, không phải vấn đề |

---

## 14. Roadmap (chia thành các implementation plan riêng)

| Plan | Scope | Output verify |
|---|---|---|
| **Plan 1** — Backend foundation | FastAPI scaffold, SQLite, models, schemas, OCR service stub, STT service stub, VN parser (full + tests), template + capture CRUD | `pytest` pass; có thể curl tạo template + upload ảnh giả + nhận OcrNumber từ stub |
| **Plan 2** — OCR + STT integration | Wire PaddleOCR thật, Whisper thật, end-to-end audio upload → parse → sum | Upload ảnh thật, ghi âm thật, nhận đúng số |
| **Plan 3** — Match engine + finalize | Matcher logic, manual match endpoints, finalize endpoint, full integration tests | Capture flow hoàn chỉnh server-side |
| **Plan 4** — Frontend foundation | Vite + React + PWA scaffold, camera, audio recorder, axios client, capture create flow | Chụp ảnh + upload thấy OCR result trên UI |
| **Plan 5** — Annotation UX | OCR overlay canvas, tick-to-correct, group panel, finalize UI, history page | Hoàn thành 1 capture đầy đủ qua UI |
| **Plan 6** — Templates UI + polish | Template CRUD UI, history detail, export JSON cho training | App dùng được hàng ngày |
| **Plan 7** (sau ~200-500 captures) | Training pipeline: dataset builder, model architecture (vision transformer hoặc YOLO + classifier), train + eval, inference endpoint thay/ bổ sung match engine. **Label cho mỗi OCR number = group_index của Match (hoặc null nếu không thuộc group nào)**. Vị trí (bbox) + crop image = feature đầu vào | Auto-classify accuracy ≥ 80% |
| **Plan 8** — Risk analysis (Bet/payout) | Mỗi group có ý nghĩa "loại cược" với multiplier = tỷ lệ thưởng (vd 80, 82, 14.5). Mỗi OCR number trong group = (số được chọn, mức cược). Tính: (a) **tổng vốn** = sum tất cả mức cược trong tất cả group; (b) **payout per number** = mức_cược × multiplier_group; (c) flag các số mà nếu trúng thì **payout > tổng vốn** (lãi cao — OK) hoặc **payout < tổng vốn** (lỗ — flag "pass"); (d) hiển thị bảng risk: mỗi số có "tỷ trọng vốn", "lãi/lỗ nếu trúng", recommend pass/take. UI có toggle bật phần này (vì là tính năng phụ, không bắt buộc cho mọi capture) | UI bảng risk hiển thị đúng với 1 capture mẫu; user có thể set "ngưỡng pass" tuỳ ý |
| **Plan 9** — Real-time streaming STT | Thay luồng "record-then-process" bằng WebSocket: client gửi audio chunk (PCM 16k, ~250ms/chunk), server dùng Whisper với VAD chunking (hoặc faster-whisper streaming, hoặc Vosk vi-model làm fallback) để trả partial transcript ngay khi user đang đọc. Frontend hiển thị các con số được parse tích lũy theo thời gian thực, dừng khi nghe "bằng" hoặc pause >1.5s | Đọc 5 số liên tiếp → thấy số xuất hiện trên UI < 1s sau khi đọc xong từng số |
| **Plan 10** — Analytics & history | Dashboard: filter theo writer_name / note_date / tag; thống kê hit-rate, ROI cumulative, profit_loss theo thời gian; biểu đồ template hay dùng nhất | Mở dashboard thấy số liệu đúng với data đã có |
| **Plan 11** — Lottery result OCR & settlement | (a) Upload ảnh KQXS (MB / MT / MN) → OCR table → detect số cột (= số đài) bằng heuristic spacing + header text matching với danh sách provinces. MB: 1 cột × 8 hàng giải × tổng 27 số đuôi. MT/MN: nhiều cột (mỗi đài 1 cột) × 9 hàng giải × tổng 18 số đuôi/đài. (b) **Preview UX**: hiển thị từng cột detected với dropdown chọn province (auto-select theo header OCR, user override được) + bảng số có thể sửa từng ô. Confirm → commit thành nhiều `LotteryDraw` records (1 per đài). **Settle ngay** sau commit: với mỗi capture status=`final` có `note_date == draw_date` và `province ∈ capture.provinces ⊆ committed_provinces`, tự động chạy settlement. (c) Settlement engine: xem §17 chi tiết bet_type semantics | Upload 1 ảnh XSMT có 2 đài → tạo 2 LotteryDraw; capture đã final với provinces=[DNG,KH] tự động settled với profit_loss đúng |

---

## 15. Out of scope (đã chốt — không làm)

- Multi-user / auth
- Cloud deployment
- Mobile native build
- Admin panel
- Monitoring stack (Prometheus / Grafana / ELK / Sentry... như trong PDF gốc)
- Backup / sync giữa các thiết bị (tạm thời)

**Sẽ làm nhưng defer sang sau MVP:**
- Real-time streaming STT (Plan 9 — sau khi MVP record-then-process chạy ổn)
- Training pipeline (Plan 7 — khi đủ ~200-500 captures)
- Risk analysis (Plan 8)
- Analytics dashboard (Plan 10)
- Lottery result OCR & settlement (Plan 11)
- MT / MN regions trong Plan 11 (chỉ MB cho version đầu)

---

## 16. Bet type semantics (chi tiết hit + payout)

Đặt: `tails_2d` = multiset 27 (MB) / 18 (MT/MN) số đuôi-2-chữ-số của 1 đài; `special_tail_2d` = đuôi 2 số của ĐB; `special_tail_3d` = đuôi 3 số của ĐB. `count(n, tails_2d)` = số lần `n` xuất hiện.

| bet_type | Số trong group | Hit per province | Payout per province (per number / per group) |
|---|---|---|---|
| `lo` | nhiều số rời rạc, mỗi số có stake riêng | `count(n, tails_2d) ≥ 1` | per number: `stake(n) × multiplier × count(n, tails_2d)` (lô kép → ăn count lần) |
| `de` | thường 1 số, có thể nhiều | `n == special_tail_2d` | per number: `stake(n) × multiplier` nếu hit, else 0 |
| `3cang` | 1 số 3-chữ-số | `n == special_tail_3d` (vd ĐB 618399 → 399) | per number: `stake(n) × multiplier` nếu hit |
| `xien_2` | đúng 2 số | tất cả 2 số đều có trong tails_2d (count ≥ 1 mỗi số) | per group: `stake_total × multiplier` nếu hit cụm; else 0 |
| `xien_3` | đúng 3 số | tất cả 3 số đều có | per group: `stake_total × multiplier` nếu hit cụm |
| `xien_4` | đúng 4 số | tất cả 4 số đều có | per group: `stake_total × multiplier` nếu hit cụm |
| `xien_quay` | N số (N ≥ 3), mỗi số stake riêng | mỗi cặp (combination C(N,2)) trong group: cặp đó hit nếu cả 2 số đều có trong tails_2d | per pair hit: `min(stake(a), stake(b)) × multiplier`. Tổng = sum tất cả pair hit |

**Multi-province**: tổng payout của capture = Σ per province × per group; tổng stake = Σ stake_per_number × N_provinces (mỗi đài cược lại từ đầu).

**Note `xien_quay`**: định nghĩa trên là 1 trong vài variant phổ biến (mỗi cặp hit ăn riêng). Nếu nhà cái dùng variant khác (vd "all-or-nothing" như xiên thường nhưng N số), config sẽ adjust ở bước implementation Plan 11. Defer detailed verification đến lúc test với case thực tế.

---

## 17. Worked example — Per-group provinces (mixed 1-đài + multi-đài)

**Capture:** `note_date = 2026-04-29`, template với 3 group, `group_provinces`:
- Group 1 (lô, ×80): `provinces = ["HN"]` (1 đài) — số `[23, 88, 74]` mỗi số stake 10k
- Group 2 (đề, ×82): `provinces = ["HN"]` (1 đài) — số `[99]` stake 5k
- Group 3 (xiên 2, ×14.5): `provinces = ["DNG", "KH"]` (2 đài) — số `[88, 74]` stake 20k

**Total stake** (mỗi group nhân theo riêng số đài của nó):
- Group 1: `(10+10+10) × 1 = 30k`
- Group 2: `5 × 1 = 5k`
- Group 3: `20 × 2 = 40k`
- **Tổng vốn = 75k**

**LotteryDraw cần có** (server tự lookup theo group_provinces × note_date):
- HN 2026-04-29: tails_2d 27 số gồm `[..., 88, 23, ..., 99, ...]`, special = `99`
- DNG 2026-04-29: tails_2d 18 số gồm `[88, 35, ..., 64]`, special = `64`
- KH 2026-04-29: tails_2d 18 số gồm `[74, 39, ..., 12]`, special = `12`

**Settlement (chỉ iterate qua các (group, province) hợp lệ):**

| Group | Province | Số | bet_type | Hit? | Payout |
|---|---|---|---|---|---|
| 1 (lô) | HN | 23 | lo | có (count=1) | 10 × 80 × 1 = 800k |
| 1 (lô) | HN | 88 | lo | có (count=1) | 10 × 80 × 1 = 800k |
| 1 (lô) | HN | 74 | lo | không | 0 |
| 2 (đề) | HN | 99 | de | có (== special HN) | 5 × 82 = 410k |
| 3 (xiên 2) | DNG | [88, 74] | xien_2 | không (88 trúng, 74 không) | 0 |
| 3 (xiên 2) | KH | [88, 74] | xien_2 | không (74 trúng, 88 không) | 0 |

- **Tổng payout = 800 + 800 + 410 = 2010k**
- **profit_loss = 2010 − 75 = +1935k**

So sánh với trường hợp cũ (provinces ở capture-level, áp tất cả group cho cả 2 đài): tổng vốn 110k → giờ chỉ 75k vì group lô/đề không cần đặt KH+DNG mà chỉ HN; tiết kiệm vốn cho các group "1 đài" — đúng tinh thần "thường chỉ đặt 1 vài con và ít, trộn chung mớ đặt 1 đài".

---

## 18. Quy ước thực thi

- **Planning / thinking tasks**: dùng Opus 4.7 (model hiện tại).
- **Code-writing tasks**: dùng Sonnet 4.6 (chuyển model khi vào Plan execution).
- Mỗi Plan ở §14 sẽ được viết thành 1 implementation plan riêng biệt qua skill `writing-plans` và execute độc lập.
