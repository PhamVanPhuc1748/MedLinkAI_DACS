from __future__ import annotations

from typing import Any

import requests

class ApiError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")

class ApiClient:
    """
    Lớp ApiClient chịu trách nhiệm giao tiếp giữa Frontend (Streamlit) và Backend (FastAPI).
    Tất cả các hành động lấy dữ liệu từ database, dự đoán bằng AI đều phải thông qua
    việc gọi API từ class này để gửi xuống Backend xử lý.
    """
    def __init__(self, base_url: str, token: str | None = None) -> None:
        """
        Khởi tạo client với địa chỉ Backend (base_url) và token xác thực (nếu đã đăng nhập).
        """
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        timeout: int = 60,
    ) -> Any:
        """
        Hàm cốt lõi để gọi HTTP Request xuống Backend.
        - Tự động gắn header `Authorization: Bearer <token>` nếu user đã đăng nhập.
        - Đóng gói dữ liệu payload thành dạng JSON để gửi đi.
        - Xử lý lỗi nếu HTTP status code >= 400 (báo lỗi Backend ném ra).
        """
        headers: dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        url = f"{self.base_url}{path}"
        response = requests.request(method=method, url=url, headers=headers, json=payload, timeout=timeout)
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise RuntimeError(f"{response.status_code}: {detail}")
        if not response.text:
            return {}
        try:
            return response.json()
        except ValueError:
            return {}

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def login(self, username: str, password: str) -> dict[str, Any]:
        return self._request("POST", "/auth/login", payload={"username": username, "password": password})

    def register(self, username: str, email: str, password: str) -> dict[str, Any]:
        return self._request(
            "POST", "/auth/register",
            payload={"username": username, "email": email, "password": password},
        )

    def forgot_password(self, username: str, email: str) -> dict[str, Any]:
        return self._request(
            "POST", "/auth/forgot-password",
            payload={"username": username, "email": email},
        )

    def reset_password(self, username: str, otp: str, new_password: str) -> dict[str, Any]:
        return self._request(
            "POST", "/auth/reset-password",
            payload={"username": username, "otp": otp, "new_password": new_password},
        )

    def predict_drug_to_disease(self, name: str, top_k: int, threshold: float, dataset: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/predict/drug-to-disease",
            payload={
                "name": str(name),
                "top_k": int(top_k),
                "threshold": float(threshold),
                "dataset": dataset,
            },
        )

    def predict_disease_to_drug(self, name: str, top_k: int, threshold: float, dataset: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/predict/disease-to-drug",
            payload={
                "name": str(name),
                "top_k": int(top_k),
                "threshold": float(threshold),
                "dataset": dataset,
            },
        )

    def history(self) -> list[dict[str, Any]]:
        return self._request("GET", "/history")

    def list_drugs(self, limit: int = 200, dataset: str | None = None) -> list[dict[str, Any]]:
        url = f"/drugs?limit={int(limit)}"
        if dataset:
            url += f"&dataset={dataset}"
        return self._request("GET", url)

    def list_diseases(self, limit: int = 200, dataset: str | None = None) -> list[dict[str, Any]]:
        url = f"/diseases?limit={int(limit)}"
        if dataset:
            url += f"&dataset={dataset}"
        return self._request("GET", url)

    def list_proteins(self, limit: int = 200) -> list[dict[str, Any]]:
        return self._request("GET", f"/proteins?limit={int(limit)}")

    def get_protein_links(self, protein_id: int) -> dict[str, Any]:
        return self._request("GET", f"/proteins/{int(protein_id)}/links")

    def list_links(self, limit: int = 300) -> list[dict[str, Any]]:
        return self._request("GET", f"/links?limit={int(limit)}")

    def stats(self) -> dict[str, Any]:
        return self._request("GET", "/stats")

    def model_metrics(self) -> dict[str, Any]:
        return self._request("GET", "/model/metrics")

    def model_compare(self, folder_path: str) -> dict[str, Any]:
        return self._request("POST", "/model/compare", payload={"folder_path": folder_path})

    def admin_recalculate_metrics(self, dataset: str) -> dict[str, Any]:
        return self._request("POST", "/admin/model/recalculate", payload={"dataset": dataset})

    def admin_seed_dataset(self, dataset: str) -> dict[str, Any]:
        return self._request("POST", "/admin/dataset/seed", payload={"dataset": dataset})

    def admin_dataset_preview(self, dataset: str) -> dict[str, Any]:
        return self._request("GET", f"/admin/dataset/{dataset}/preview")

    def admin_stats(self) -> dict[str, Any]:
        return self._request("GET", "/admin/stats")

    def admin_prediction_direction_stats(self) -> list[dict[str, Any]]:
        return self._request("GET", "/admin/stats/predictions-by-direction")

    def admin_predictions(self, limit: int = 300) -> list[dict[str, Any]]:
        return self._request("GET", f"/admin/predictions?limit={int(limit)}")

    def admin_save_drug(self, drug_id: int, name: str, external_id: str | None, smiles: str | None) -> dict[str, Any]:
        return self._request(
            "POST",
            "/admin/drugs",
            payload={"id": int(drug_id), "name": str(name), "external_id": external_id, "smiles": smiles},
        )

    def admin_save_disease(self, disease_id: int, name: str) -> dict[str, Any]:
        return self._request("POST", "/admin/diseases", payload={"id": int(disease_id), "name": str(name)})

    def admin_save_link(self, drug_id: int, disease_id: int) -> dict[str, Any]:
        return self._request("POST", "/admin/links", payload={"drug_id": int(drug_id), "disease_id": int(disease_id)})

    # ── Database Management ───────────────────────────────────────────────────
    def db_status(self) -> dict[str, Any]:
        """Kiểm tra trạng thái kết nối database."""
        return self._request("GET", "/db/status")

    def admin_db_setup(self) -> dict[str, Any]:
        """Chạy setup_database.py để tự động kết nối SQL Server (Admin only)."""
        return self._request("POST", "/admin/db/setup", timeout=130)

    def evaluate_model(self, file_content: bytes, filename: str, dataset: str) -> dict[str, Any]:
        """Upload và đánh giá model .pth tùy chọn."""
        url = f"{self.base_url}/model/evaluate"
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            
        files = {"file": (filename, file_content, "application/octet-stream")}
        data = {"dataset": dataset}
        
        try:
            resp = requests.post(url, headers=headers, files=files, data=data, timeout=300)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            err_detail = str(e)
            try:
                err_json = resp.json()
                if "detail" in err_json:
                    err_detail = str(err_json["detail"])
            except ValueError:
                pass
            raise ApiError(resp.status_code, err_detail) from e
        except requests.exceptions.RequestException as e:
            raise ApiError(0, f"Loi ket noi den {url}: {e}") from e

    def inspect_model(self, file_content: bytes, filename: str) -> dict[str, Any]:
        """Kiểm tra cấu trúc file .pth."""
        url = f"{self.base_url}/model/inspect"
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            
        files = {"file": (filename, file_content, "application/octet-stream")}
        
        try:
            resp = requests.post(url, headers=headers, files=files, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            err_detail = str(e)
            try:
                err_json = resp.json()
                if "detail" in err_json:
                    err_detail = str(err_json["detail"])
            except ValueError:
                pass
            raise ApiError(resp.status_code, err_detail) from e
        except requests.exceptions.RequestException as e:
            raise ApiError(0, f"Loi ket noi den {url}: {e}") from e
