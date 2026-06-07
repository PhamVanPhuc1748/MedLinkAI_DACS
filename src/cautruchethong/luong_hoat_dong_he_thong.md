# Luồng Hoạt Động Tổng Thể Của Hệ Thống MedLink (End-to-End Data Flow)

Hệ thống MedLink là một ứng dụng Web hiện đại được chia làm 3 tầng (3-Tier Architecture) biệt lập. Tài liệu này sẽ giải phẫu chi tiết cách dữ liệu chảy từ ổ cứng (file `.json`, SQL) chạy lên giao diện người dùng và ngược lại.

---

## 1. Bức Tranh Toàn Cảnh (The Big Picture)

Hệ thống hoạt động qua 4 thành phần chính giao tiếp liên tục với nhau:

1.  **Frontend (Web UI - Streamlit):** Chạy ở cổng `8502`. Là nơi người dùng thao tác.
2.  **API Bridge (Cầu nối):** Nằm trong file `api_client.py`. Đóng vai trò làm "Người vận chuyển" gói hàng giữa UI và Backend.
3.  **Backend (Core - FastAPI):** Chạy ở cổng `8000`. Cung cấp các API xử lý logic (Tính toán AI, check mật khẩu, CRUD).
4.  **Database (Dữ liệu - SQL/JSON):** Nơi lưu trữ vĩnh viễn (Persistent storage).

```text
[Người Dùng] 
     │ (Click, Gõ phím)
     ▼
[Frontend: Streamlit] (Hiển thị Bảng, Đồ thị Pyvis)
     │ (Dùng ApiClient, gắn Token bảo mật)
     ▼ HTTP POST/GET (Cổng 8000)
[Backend: FastAPI Routes] 
     │ (Kiểm tra quyền, gọi AI Model)
     ▼
[Database Repo] 
     │ (Đọc/Ghi)
     ▼
(SQL Server) <== Đồng bộ ngầm liên tục ==> (Thư mục /data/*.json)
```

---

## 2. Lớp Dữ Liệu: Tại sao lại có cả SQL Server lẫn file .JSON?

Đây là cơ chế **"Lưu trữ Lai" (Hybrid Storage)** siêu an toàn được cài đặt trong `src/backend/app/database.py`.

*   **Chế độ ưu tiên:** Khi khởi động, Backend cố gắng kết nối với SQL Server. Mọi truy vấn (Lấy danh sách thuốc, lưu lịch sử) đều chạy qua SQL để đảm bảo tính toàn vẹn và tốc độ.
*   **Cơ chế Fallback (Dự phòng):** Nếu SQL Server bị sập hoặc chưa cài đặt, hệ thống *lập tức chuyển sang đọc/ghi trực tiếp vào các file `.json`* trong thư mục `src/data/` (ví dụ: `drugs.json`, `users.json`). Người dùng sẽ không hề biết hệ thống bị rớt DB.
*   **Đồng bộ ngầm (Realtime Sync):** Backend mở một luồng chạy ngầm (Background Thread). Mỗi khi có data mới (ví dụ có người đăng ký tài khoản mới vào SQL), luồng ngầm này sẽ tự động **xuất (dump) dữ liệu từ SQL ghi đè ra file JSON tương ứng**. Nhờ vậy, file JSON luôn là bản Backup tươi mới nhất.

---

## 3. Lớp Backend API (FastAPI)

Nằm chủ yếu ở thư mục `src/backend/app/api/`. Nó không có giao diện, chỉ có các đường dẫn (Endpoint).

*   **Ví dụ 1 API:** Mở file `routes.py`, bạn sẽ thấy:
    ```python
    @router.get("/data/drugs")
    def get_all_drugs():
        return repo.get_all_drugs()
    ```
    Khi có ai đó gọi vào link `http://localhost:8000/api/data/drugs`, hàm này chạy, lấy data từ Data Layer (như nói ở phần 2) và biến đổi chúng thành dạng JSON text để ném trả về cho người gọi.

*   **Bảo mật:** Backend bảo vệ các API quan trọng bằng cách đòi hỏi **Token JWT**. Nếu không có token hợp lệ trong Header, Backend sẽ từ chối trả lời (Mã lỗi 401 Unauthorized).

---

## 4. Lớp Giao Tiếp (The API Client)

Tại sao Frontend không gọi trực tiếp Database? Vì làm vậy rất kém bảo mật và không thể tách rời (Decoupled).
Hệ thống sử dụng file `src/frontend/app/services/api_client.py` làm "Đại sứ quán".

**Cách ApiClient hoạt động:**
1.  Frontend không tự viết lệnh `requests.get(...)` rải rác khắp nơi.
2.  Mọi request đều qua hàm trung tâm `ApiClient._request(...)`.
3.  Hàm này tự động lục trong túi `st.session_state` xem người dùng đã đăng nhập chưa. Nếu có token, nó tự động dán token vào Header (`"Authorization": f"Bearer {token}"`) rồi mới gửi xuống Backend.
4.  Nếu Backend báo lỗi (ví dụ: mất mạng, lỗi AI), `ApiClient` sẽ túm lấy lỗi đó và dịch ra thông báo dễ hiểu cho Frontend hiển thị.

---

## 5. Tầng Giao Diện Web (Streamlit)

File gốc khởi động là `src/frontend/app_modern.py`. 
Vì Streamlit có một nhược điểm lớn là **chạy lại toàn bộ code từ trên xuống dưới mỗi khi người dùng ấn nút**, hệ thống đã xử lý bằng cơ chế Session State.

*   **Quản lý Trạng Thái (`st.session_state`):** Khi người dùng Login thành công, Token, Role (Quyền admin/user), và Tên người dùng được lưu cứng vào RAM của Streamlit. Kể cả khi trang tự tải lại, trạng thái đăng nhập vẫn còn nguyên.
*   **Routing (Định tuyến):** Tùy thuộc vào việc `st.session_state` đang trỏ đến trang nào (Home, Predict, Admin Dashboard), Streamlit sẽ nạp giao diện tương ứng từ thư mục `src/frontend/app/pages/`.
*   **Hiển thị:** Dữ liệu JSON khô khan trả về từ Backend được Streamlit biến thành các Bảng (DataFrame), Biểu đồ thống kê, và đặc biệt là vẽ ra không gian Lưới sinh học 3D bằng thư viện Pyvis (JavaScript).

---

## 6. Mổ Xẻ Thực Tế: Chuyện Gì Xảy Ra Khi Bấm Nút "Dự Đoán"?

Hãy xem luồng End-to-End của tính năng quan trọng nhất:

1.  **UI:** Trên trang Web, người dùng nhập tên thuốc "Aspirin" và nhấn nút "Dự đoán".
2.  **API Client:** Giao diện gọi hàm `api_client.predict_drug_to_disease("Aspirin")`. Hàm này đóng gói chữ "Aspirin" gửi qua mạng (HTTP POST) xuống Backend cổng 8000.
3.  **Backend Route:** File `routes.py` hứng Request tại endpoint `/predict/drug-to-disease`.
4.  **AI Service:** Route gọi module AI (`inference_service.py`).
    - AI tìm "Aspirin" trong từ điển, lấy ra được Index (ví dụ ID: 12).
    - AI nạp mô hình FuzzyGCN và tệp trọng số `best_fold.pth`.
    - AI chạy Forward Pass (Tính toán nơ-ron như đã giải thích ở tài liệu trước).
    - AI lọc ra Top 50 Bệnh có điểm Logit cao nhất.
5.  **Lưu Lịch Sử:** Trước khi trả kết quả, Backend gọi hàm `repo.add_prediction()` để lưu lại vết "Ông A vừa tìm Aspirin" xuống SQL Server (sau đó luồng ngầm sẽ copy dòng này sang JSON).
6.  **Trả Kết Quả:** Backend gỡ các ID bệnh thành chữ tiếng Việt (Ví dụ: "Đau đầu") và trả về mạng cục bộ 1 gói JSON.
7.  **Render:** Web nhận gói JSON. Streamlit vẽ 1 cái Bảng báo cáo kết quả và vẽ 1 đồ thị mạng nhện nối "Aspirin" với 50 bệnh đó. Quá trình kết thúc.
