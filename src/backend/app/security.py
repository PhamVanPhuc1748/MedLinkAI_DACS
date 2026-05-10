from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

# ── Cố gắng dùng passlib[bcrypt]; nếu chưa cài thì fallback sha256 ─────────
try:
    from passlib.context import CryptContext
    _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    _BCRYPT_OK = True
except ImportError:  # pragma: no cover
    _BCRYPT_OK = False


def _is_legacy_sha256(password_hash: str) -> bool:
    """
    Hash SHA-256 thuần: dài đúng 64 ký tự hex, KHÔNG bắt đầu bằng '$'.
    Hash bcrypt bắt đầu bằng '$2b$' hoặc '$2a$' nên dễ phân biệt.
    """
    return len(password_hash) == 64 and not password_hash.startswith("$")


def hash_password(password: str) -> str:
    """Băm mật khẩu bằng bcrypt (nếu có passlib) hoặc sha256 (fallback)."""
    if _BCRYPT_OK:
        return _pwd_ctx.hash(password)
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """
    Xác thực mật khẩu với tương thích ngược:
    - Nếu hash cũ (sha256, 64 ký tự hex) → so sánh sha256.
    - Nếu hash mới (bcrypt, bắt đầu '$') → dùng passlib verify.
    """
    if _is_legacy_sha256(password_hash):
        # Tương thích ngược: hash cũ dùng sha256
        return hashlib.sha256(password.encode("utf-8")).hexdigest() == password_hash
    if _BCRYPT_OK:
        return _pwd_ctx.verify(password, password_hash)
    # Fallback cuối cùng nếu không có passlib và hash không phải sha256
    return hashlib.sha256(password.encode("utf-8")).hexdigest() == password_hash


def create_token() -> str:
    return secrets.token_urlsafe(32)


@dataclass
class AuthUser:
    id: int
    username: str
    role: str
