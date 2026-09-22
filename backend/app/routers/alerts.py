"""
Alert endpoints — FR-5.2 (fetch for dashboard), FR-5.5 (acknowledge).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app import schemas

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("/", response_model=list[schemas.AlertOut])
def list_alerts(db: Session = Depends(get_db)):
    return db.query(models.Alert).order_by(models.Alert.timestamp.desc()).all()


@router.patch("/{alert_id}/acknowledge", response_model=schemas.AlertOut)
def acknowledge_alert(alert_id: str, db: Session = Depends(get_db)):
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = True
    db.commit()
    db.refresh(alert)
    return alert
