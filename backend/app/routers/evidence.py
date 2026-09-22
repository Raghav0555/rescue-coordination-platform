"""
Evidence endpoints — FR-2.1, FR-2.2, FR-2.4.
Submitting evidence triggers the fusion engine (UC-2 in the SRS) and,
if the resulting confidence score crosses the threshold, generates an
alert automatically — matching the Sequence Diagram flow.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app import schemas
from app.services.fusion_engine import fuse_evidence
from app.services.alert_service import check_and_generate_alert

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.post("/", response_model=schemas.EvidenceOut)
def submit_evidence(payload: schemas.EvidenceCreate, db: Session = Depends(get_db)):
    # FR-2.4: basic plausibility validation
    if not (-90 <= payload.lat <= 90) or not (-180 <= payload.lng <= 180):
        raise HTTPException(status_code=400, detail="Invalid coordinates")

    evidence = models.Evidence(
        type=payload.type,
        lat=payload.lat,
        lng=payload.lng,
        source_device_id=payload.source_device_id,
        note=payload.note,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    # UC-2: fuse immediately after submission
    zone = fuse_evidence(db, evidence)
    # FR-5.1: check threshold right after the score updates
    check_and_generate_alert(db, zone)

    return evidence


@router.get("/", response_model=list[schemas.EvidenceOut])
def list_evidence(db: Session = Depends(get_db)):
    return db.query(models.Evidence).order_by(models.Evidence.timestamp.desc()).all()


@router.get("/zones", response_model=list[schemas.ZoneOut])
def list_zones(db: Session = Depends(get_db)):
    """Powers the dashboard confidence heatmap (FR-6.1)."""
    return db.query(models.SurvivorZone).all()
