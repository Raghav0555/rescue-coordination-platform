"""
Report endpoints — FR-6.3 (operational summary) and FR-6.4 (CSV export).
"""
import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/summary")
def report_summary_json(db: Session = Depends(get_db)):
    """FR-6.3: operational summary as JSON — zones, evidence counts, task/alert status."""
    zones = db.query(models.SurvivorZone).all()
    result = []
    for z in zones:
        evidence_count = db.query(models.Evidence).filter(models.Evidence.zone_id == z.id).count()
        tasks = db.query(models.Task).filter(models.Task.zone_id == z.id).all()
        alerts = db.query(models.Alert).filter(models.Alert.zone_id == z.id).count()
        result.append({
            "zone_id": z.id,
            "lat": z.lat,
            "lng": z.lng,
            "confidence_score": z.confidence_score,
            "status": z.status,
            "evidence_count": evidence_count,
            "task_count": len(tasks),
            "alert_count": alerts,
            "last_updated": z.last_updated.isoformat(),
        })
    return result


@router.get("/summary.csv")
def report_summary_csv(db: Session = Depends(get_db)):
    """FR-6.4: same summary, exported as a downloadable CSV file."""
    zones = db.query(models.SurvivorZone).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["zone_id", "lat", "lng", "confidence_score", "status", "evidence_count", "task_count", "alert_count", "last_updated"])

    for z in zones:
        evidence_count = db.query(models.Evidence).filter(models.Evidence.zone_id == z.id).count()
        task_count = db.query(models.Task).filter(models.Task.zone_id == z.id).count()
        alert_count = db.query(models.Alert).filter(models.Alert.zone_id == z.id).count()
        writer.writerow([z.id, z.lat, z.lng, z.confidence_score, z.status, evidence_count, task_count, alert_count, z.last_updated.isoformat()])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=rescue_operation_report.csv"},
    ) 