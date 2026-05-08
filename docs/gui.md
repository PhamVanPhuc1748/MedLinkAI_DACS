# Tài Liệu Giao Diện Web (GUI) — MedLink AI

## 1. Tổng Quan

Giao diện được xây dựng bằng **Streamlit**, giao tiếp với **FastAPI backend** thông qua lớp `ApiClient`. Toàn bộ trạng thái đăng nhập lưu trong `st.session_state`.

**Điểm vào:** `frontend/streamlit_app.py`  
**Chạy:** `streamlit run frontend/streamlit_app.py` (từ thư mục gốc `model_GNN/`)  
**URL mặc định:** http://localhost:8501

---

## 2. Cấu Trúc Thư Mục Frontend

```
frontend/
├── streamlit_app.py          ← Điểm vào, khởi tạo layout chính + sidebar
└── app/
    ├── config.py             ← API_DEFAULT URL
    ├── state.py              ← Helper đọc/xóa session_state (token, role, username)
    ├── pages/
    │   ├── auth.py           ← Trang đăng nhập (render_login)
    │   ├── user.py           ← Workspace tra cứu (render_user_workspace)
    │   └── admin.py          ← Admin console (render_admin_console)
    ├── services/
    │   └── api_client.py     ← HTTP client bọc requests → FastAPI
    └── ui/
        ├── theme.py          ← apply_theme() CSS toàn cục + render_hero()
        └── components.py     ← show_split_result_table, show_history_table, show_metric_row, card_open/close
```

---

## 3. Luồng Điều Hướng (Navigation Flow)

```
streamlit_app.py::main()
        │
        ├─── [Sidebar] api_base_url input + nút "Kiểm tra API"
        │
        ├─── Chưa đăng nhập ──────────────────────────────▶ render_login()
        │                                                         │
        │                                              POST /auth/login
        │                                                         │
        │                                         Lưu token/role vào session_state
        │                                                         │
        │                                                    st.rerun()
        │
        ├─── Đã đăng nhập (role=user) ────────────────────▶ render_user_workspace()
        │       sidebar: radio ["🔬 Dự đoán"]
        │
        └─── Đã đăng nhập (role=admin) ───────────────────▶ render_user_workspace()
                sidebar: radio ["🔬 Dự đoán", "🛠️ Admin Console"]
                                              └──────────▶ render_admin_console()
```

---

## 4. Trang Đăng Nhập (`pages/auth.py`)

**Hàm:** `render_login(api_base_url: str)`

- Layout 3 cột: `[1, 2, 1]` — card đăng nhập nằm ở cột giữa
- Gọi `client.login(username, password)` → nhận `token`, `username`, `role`
- Lưu vào session: `st.session_state["token"]`, `["username"]`, `["role"]`
- Gọi `st.rerun()` để chuyển sang workspace

---

## 5. Workspace Người Dùng (`pages/user.py`)

**Hàm:** `render_user_workspace(api_base_url: str, token: str)`

Gồm 3 tab:

### Tab A — 💊 Thuốc → Bệnh

| Element | Mô tả |
|---------|-------|
| Form input | Tên thuốc (text), Dataset (selectbox), Top-K (slider 1–50), Ngưỡng (slider 0.0–1.0) |
| Submit | POST `/predict/drug-to-disease` |
| Kết quả | `show_split_result_table(results, entity_label="Tên bệnh")` |
| Sau predict | `st.session_state.pop("history_rows")` — invalidate cache lịch sử |

### Tab B — 🦠 Bệnh → Thuốc

Tương tự Tab A, gọi POST `/predict/disease-to-drug`, hiển thị `entity_label="Tên thuốc"`.

### Tab C — 📋 Lịch Sử

- Lần đầu render hoặc sau khi `history_rows` bị pop → gọi `client.history()` → lưu vào `session_state["history_rows"]`
- Nút "🔄 Tải lại" xóa cache và reload
- Hiển thị qua `show_history_table(rows)`: bảng `st.dataframe` với cột `direction | input_name | target_name | score (%) | timestamp`

---

## 6. Admin Console (`pages/admin.py`)

**Hàm:** `render_admin_console(api_base_url: str, token: str)`

Gồm 4 tab:

| Tab | Nội dung |
|-----|---------|
| 💊 Quản lý Thuốc | Danh sách thuốc, form thêm mới (id, name, external_id, smiles) |
| 🦠 Quản lý Bệnh | Danh sách bệnh, form thêm bệnh mới |
| 🔗 Liên kết | Danh sách drug–disease links, form thêm liên kết |
| 📋 Prediction Logs | Toàn bộ lịch sử dự đoán của mọi user, metric tổng quan (`show_metric_row`) |

---

## 7. Component Hiển Thị Kết Quả (`ui/components.py`)

### `show_split_result_table(results, entity_label)`

Nhận `list[dict]` — mỗi dict có: `name`, `score` (0–1), `known` (bool).

**Phân loại:**
```python
df_tri_benh = [r for r in results if r.get("known", False)]     # known=True
df_canh_bao = [r for r in results if not r.get("known", False)] # known=False
```

**Hiển thị:**
```
┌──────────────────────────────┬──────────────────────────────────┐
│  ✅ Nhóm Thuốc Điều Trị      │  ⚠️ Nhóm Nguy Cơ / Tác Dụng Phụ │
│  (liên kết đã xác nhận)      │  (AI dự đoán, cần kiểm chứng)   │
│  _render_group_table(...)    │  _render_group_table(...)        │
│  hoặc st.info() nếu rỗng    │  hoặc st.info() nếu rỗng        │
└──────────────────────────────┴──────────────────────────────────┘
```

Mỗi bảng gồm cột: `# | Tên | Trạng thái badge | Điểm dự đoán (progress bar)`

### `show_result_table(results, entity_label)` _(legacy)_

Bảng gộp một cột, giữ lại để tương thích ngược. **Không dùng trên UI chính.**

### `show_history_table(rows)`

Parse `list[dict]` từ `/history` API thành `pd.DataFrame`, map direction sang emoji label.

### `show_metric_row(stats)`

Metric cards ngang 5 cột màu sắc nổi bật (dùng trong Admin — Prediction Logs).

### `card_open(title, icon)` / `card_close()`

Bọc section trong `<div class="card">`, dùng cặp đôi.

---

## 8. Hệ Thống CSS (`ui/theme.py`)

**Hàm:** `apply_theme()` — gọi ở đầu `main()`, inject CSS qua `st.markdown(..., unsafe_allow_html=True)`

### CSS Classes Quan Trọng

| Class | Màu sắc | Dùng cho |
|-------|---------|---------|
| `.badge-known` | Nền `#dcfce7` xanh lá · Chữ `#14532d` · Viền `#4ade80` | Badge ✅ kết quả đã xác nhận |
| `.badge-pred` | Nền `#fef9c3` vàng · Chữ `#713f12` · Viền `#facc15` | Badge 🔬 AI dự đoán mới |
| `.result-table` | Table HTML tùy chỉnh | Bảng kết quả dự đoán |
| `.score-bar-fill` | Gradient `#0d9488 → #1e40af` | Progress bar điểm xác suất |
| `.card` | Nền trắng, border `#e2e8f0`, shadow nhẹ | Container section |
| `.info-box` | Nền `#eff6ff`, border trái xanh | Thông báo hướng dẫn |
| `.warn-box` | Nền `#fffbeb`, border trái vàng | Cảnh báo |
| `.hero-banner` | Gradient `#0d9488 → #1e40af` | Banner đầu trang |

---

## 9. Quản Lý Session State

| Key | Kiểu | Ý nghĩa |
|-----|------|---------|
| `token` | `str` | Bearer token từ `/auth/login` |
| `username` | `str` | Tên người dùng đang đăng nhập |
| `role` | `str` | `"user"` hoặc `"admin"` |
| `history_rows` | `list[dict] \| None` | Cache lịch sử tra cứu; `None` → trigger re-fetch |

`history_rows` bị xóa (`pop`) sau mỗi lần predict thành công → Tab C tự fetch lại khi được mở.

---

## 10. Khởi Động & Debug

```bash
# Backend (terminal 1)
cd E:\code\model_GNN
venv\Scripts\activate
python backend/main.py
# → http://localhost:8000  |  Swagger: http://localhost:8000/docs

# Frontend (terminal 2)
cd E:\code\model_GNN
venv\Scripts\activate
streamlit run frontend/streamlit_app.py
# → http://localhost:8501
```

**Lỗi thường gặp:**

| Triệu chứng | Nguyên nhân | Cách fix |
|-------------|-------------|---------|
| `File does not exist: streamlit_app.py` | Chạy sai thư mục | Phải chạy từ `model_GNN/`, không phải từ `frontend/` |
| `❌ Offline` khi bấm Kiểm tra API | Backend chưa chạy | Chạy `python backend/main.py` trước |
| Badge màu không hiển thị | CSS variable không propagate | Đã fix: dùng hex cứng trong `.badge-known` và `.badge-pred` |
| Lịch sử không cập nhật | Cache cũ trong session | Bấm "🔄 Tải lại" hoặc predict mới → cache tự xóa |
