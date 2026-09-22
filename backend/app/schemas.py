"""
Pydantic schemas — request/response shapes for the API.
These match the sample payloads in the SRS Appendix D.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ---------- Auth (FR-1.1, FR-1.2) ----------
class UserCreate(BaseModel):
    name: str
    role: str
    contact_number: Optional[str] = None
    password: str
    team_id: Optional[str] = None


class UserOut(BaseModel):
    id: str
    name: str
    role: str
    team_id: Optional[str] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    name: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


# ---------- Evidence (FR-2.1, FR-2.2) ----------
class EvidenceCreate(BaseModel):
    type: str
    lat: float
    lng: float
    source_device_id: Optional[str] = None
    note: Optional[str] = None


class EvidenceOut(BaseModel):
    id: str
    type: str
    lat: float
    lng: float
    timestamp: datetime
    zone_id: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- Zone / Fusion (FR-3.x) ----------
class ZoneOut(BaseModel):
    id: str
    lat: float
    lng: float
    confidence_score: int
    status: str
    last_updated: datetime

    class Config:
        from_attributes = True


# ---------- Team (FR-4.1) ----------
class TeamCreate(BaseModel):
    team_name: str


class TeamLocationUpdate(BaseModel):
    lat: float
    lng: float


class TeamOut(BaseModel):
    id: str
    team_name: str
    current_lat: Optional[float]
    current_lng: Optional[float]
    status: str

    class Config:
        from_attributes = True


# ---------- Task (FR-4.2, FR-4.3, FR-4.4) ----------
class TaskCreate(BaseModel):
    zone_id: str
    team_id: str
    priority: str = "Medium"


class TaskStatusUpdate(BaseModel):
    status: str


class TaskOut(BaseModel):
    id: str
    zone_id: str
    team_id: Optional[str]
    priority: str
    status: str

    class Config:
        from_attributes = True


# ---------- Alert (FR-5.1, FR-5.2) ----------
class AlertOut(BaseModel):
    id: str
    zone_id: str
    trigger_score: int
    priority: str
    acknowledged: bool
    timestamp: datetime

    class Config:
        from_attributes = True
