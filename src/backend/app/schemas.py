from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=6)


class ForgotPasswordRequest(BaseModel):
    username: str
    email: str


class ResetPasswordRequest(BaseModel):
    username: str
    otp: str
    new_password: str = Field(min_length=6)


class PredictRequest(BaseModel):
    name: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)
    threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    dataset: str = Field(default="B-dataset")


class PredictionItem(BaseModel):
    id: int
    name: str
    score: float
    known: bool = False


class PredictResponse(BaseModel):
    direction: str
    input_name: str
    results: list[PredictionItem]


class HistoryItem(BaseModel):
    id: int
    direction: str
    input_name: str
    target_id: int
    target_name: str
    score: float
    known: bool = False
    timestamp: datetime


class DrugIn(BaseModel):
    id: int
    name: str
    external_id: str | None = None
    smiles: str | None = None


class DiseaseIn(BaseModel):
    id: int
    name: str


class LinkIn(BaseModel):
    drug_id: int
    disease_id: int


class StatsResponse(BaseModel):
    total_users: int
    total_drugs: int
    total_diseases: int
    total_links: int
    total_predictions: int


class ModelCompareRequest(BaseModel):
    folder_path: str = Field(min_length=1)


class AdminRecalcRequest(BaseModel):
    dataset: str = Field(min_length=1)


class SeedDatasetRequest(BaseModel):
    dataset: str = Field(min_length=1)
