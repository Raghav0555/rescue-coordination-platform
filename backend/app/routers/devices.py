"""
Device endpoints — supports FR-3.5 (device health weighting) and
FR-9-equivalent health tracking. A device "registers" itself (or gets
upserted) whenever its health is reported, so the Fusion Engine has
something to look up when scoring evidence from it.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import datetime

from app.db.database import get_db
from app.db import models
from pydantic import BaseModel

router = APIRouter(prefix="/api/devices", tags=["devices"])


class DeviceHealthUpdate(BaseModel):
    id: str
    type: str = "MobileApp"
    battery_level: int = 100


class DeviceOut(BaseModel):
    id: str
    type: str
    battery_level: int
    last_calibration: datetime.datetime
    last_seen: datetime.datetime

    class Config:
        from_attributes = True


@router.post("/health", response_model=DeviceOut)
def report_device_health(payload: DeviceHealthUpdate, db: Session = Depends(get_db)):
    """Upsert: creates the device record on first report, updates it after."""
    device = db.query(models.Device).filter(models.Device.id == payload.id).first()
    if not device:
        device = models.Device(id=payload.id, type=payload.type, battery_level=payload.battery_level)
        db.add(device)
    else:
        device.battery_level = payload.battery_level
        device.last_seen = datetime.datetime.utcnow()
    db.commit()
    db.refresh(device)
    return device


@router.get("/", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db)):
    return db.query(models.Device).all()