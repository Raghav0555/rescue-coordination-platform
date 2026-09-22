"""
Alert Service — implements FR-5.1, FR-5.2, FR-5.4.
Checks a zone's confidence score against the alert threshold and creates
an Alert record if it's crossed. In the full build this would also push
over the WebSocket channel to the dashboard; the prototype just persists
the alert and lets the dashboard poll for it.
"""
from sqlalchemy.orm import Session
from app.db import models
from app.services.fusion_engine import ALERT_THRESHOLD


def check_and_generate_alert(db: Session, zone: models.SurvivorZone) -> models.Alert | None:
    """FR-5.1: only fires when the score crosses the threshold."""
    if zone.confidence_score < ALERT_THRESHOLD:
        return None

    # Avoid spamming duplicate alerts for the same zone at the same score
    existing = (
        db.query(models.Alert)
        .filter(models.Alert.zone_id == zone.id, models.Alert.acknowledged == False)  # noqa: E712
        .first()
    )
    if existing and existing.trigger_score >= zone.confidence_score:
        return existing

    priority = "Critical" if zone.confidence_score >= 90 else "High"
    alert = models.Alert(
        zone_id=zone.id,
        trigger_score=zone.confidence_score,
        priority=priority,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
