from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class User(Base):
    __tablename__ = "nguoi_dung"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)

    predictions: Mapped[List[PredictionHistory]] = relationship(
        "PredictionHistory",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Drug(Base):
    __tablename__ = "thuoc"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    smiles: Mapped[str | None] = mapped_column(Text, nullable=True)
    features: Mapped[str | None] = mapped_column(Text, nullable=True)


class Disease(Base):
    __tablename__ = "benh"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    features: Mapped[str | None] = mapped_column(Text, nullable=True)


class DrugDiseaseLink(Base):
    __tablename__ = "lien_ket_thuoc_benh"
    __table_args__ = (UniqueConstraint("drug_id", "disease_id", name="uq_drug_disease"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    drug_id: Mapped[int] = mapped_column(ForeignKey("thuoc.id"), nullable=False, index=True)
    disease_id: Mapped[int] = mapped_column(ForeignKey("benh.id"), nullable=False, index=True)


class Protein(Base):
    __tablename__ = "protein"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    accession: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    sequence: Mapped[str | None] = mapped_column(Text, nullable=True)


class DrugProteinLink(Base):
    __tablename__ = "lien_ket_thuoc_protein"
    __table_args__ = (UniqueConstraint("drug_id", "protein_id", name="uq_drug_protein"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    drug_id: Mapped[int] = mapped_column(ForeignKey("thuoc.id"), nullable=False, index=True)
    protein_id: Mapped[int] = mapped_column(ForeignKey("protein.id"), nullable=False, index=True)


class ProteinDiseaseLink(Base):
    __tablename__ = "lien_ket_protein_benh"
    __table_args__ = (UniqueConstraint("protein_id", "disease_id", name="uq_protein_disease"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    protein_id: Mapped[int] = mapped_column(ForeignKey("protein.id"), nullable=False, index=True)
    disease_id: Mapped[int] = mapped_column(ForeignKey("benh.id"), nullable=False, index=True)


class PredictionHistory(Base):
    __tablename__ = "lich_su_du_doan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("nguoi_dung.id"), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(32), nullable=False)
    input_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_name: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    known: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="0")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped[User] = relationship("User", back_populates="predictions")


# ── Bảng riêng theo từng dataset (abstract base classes) ─────────────────────

class _ThuocBase(Base):
    """Lưu danh sách thuốc của một dataset cụ thể."""
    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    local_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    smiles: Mapped[str | None] = mapped_column(Text, nullable=True)


class ThuocB(_ThuocBase):
    """Danh sách thuốc – B-dataset."""
    __tablename__ = "thuoc_b"


class ThuocC(_ThuocBase):
    """Danh sách thuốc – C-dataset."""
    __tablename__ = "thuoc_c"


class ThuocF(_ThuocBase):
    """Danh sách thuốc – F-dataset."""
    __tablename__ = "thuoc_f"


class _BenhBase(Base):
    """Lưu danh sách bệnh của một dataset cụ thể."""
    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    local_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)


class BenhB(_BenhBase):
    """Danh sách bệnh – B-dataset."""
    __tablename__ = "benh_b"


class BenhC(_BenhBase):
    """Danh sách bệnh – C-dataset."""
    __tablename__ = "benh_c"


class BenhF(_BenhBase):
    """Danh sách bệnh – F-dataset."""
    __tablename__ = "benh_f"


class _ProteinBase(Base):
    """Lưu danh sách protein của một dataset cụ thể."""
    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    local_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    accession: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    sequence: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProteinB(_ProteinBase):
    """Danh sách protein – B-dataset."""
    __tablename__ = "protein_b"


class ProteinC(_ProteinBase):
    """Danh sách protein – C-dataset."""
    __tablename__ = "protein_c"


class ProteinF(_ProteinBase):
    """Danh sách protein – F-dataset."""
    __tablename__ = "protein_f"


class _LienKetBase(Base):
    """Lưu liên kết thuốc–bệnh của một dataset cụ thể."""
    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    drug_local_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    disease_local_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)


class LienKetB(_LienKetBase):
    """Liên kết thuốc–bệnh – B-dataset."""
    __tablename__ = "lien_ket_b"


class LienKetC(_LienKetBase):
    """Liên kết thuốc–bệnh – C-dataset."""
    __tablename__ = "lien_ket_c"


class LienKetF(_LienKetBase):
    """Liên kết thuốc–bệnh – F-dataset."""
    __tablename__ = "lien_ket_f"

