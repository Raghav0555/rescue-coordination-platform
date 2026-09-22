"""
Fusion Engine — implements FR-3.1 through FR-3.4.

For the prototype, spatial correlation is done with a simple haversine
distance check (in Python) instead of a PostGIS ST_DWithin query, and
temporal correlation is a plain timestamp window check. This keeps the
prototype dependency-free; swapping to PostGIS later just means replacing
`find_nearby_evidence` with a spatial SQL query.
"""
import math
import datetime
from sqlalchemy.orm import Session

from app.db import models

# Configurable fusion parameters (FR-8.4) — hardcoded here for the prototype,
# would come from an admin-editable config table in the full build.
CORRELATION_RADIUS_METERS = 50
TIME_WINDOW_MINUTES = 30
ALERT_THRESHOLD = 75

# Weight given to each evidence type when computing confidence (FR-3.3).
# Thermal and audio (survivor-specific signals) count more than a bare GPS ping.
EVIDENCE_WEIGHTS = {
    "Thermal": 30,
    "Audio": 25,
    "Visual": 20,
    "Sensor": 15,
    "GPS": 10,
}


def haversine_distance_m(lat1, lng1, lat2, lng2):
    """Distance between two lat/lng points in meters."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def find_or_create_zone(db: Session, lat: float, lng: float) -> models.SurvivorZone:
    """
    FR-3.1: correlate new evidence with an existing zone within the
    correlation radius, or create a new zone if none is nearby.
    """
    zones = db.query(models.SurvivorZone).all()
    for zone in zones:
        if haversine_distance_m(lat, lng, zone.lat, zone.lng) <= CORRELATION_RADIUS_METERS:
            return zone

    zone = models.SurvivorZone(lat=lat, lng=lng, confidence_score=0)
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


def get_recent_evidence_for_zone(db: Session, zone_id: str):
    """FR-3.2: only correlate evidence within the configured time window."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=TIME_WINDOW_MINUTES)
    return (
        db.query(models.Evidence)
        .filter(models.Evidence.zone_id == zone_id, models.Evidence.timestamp >= cutoff)
        .all()
    )


def calculate_confidence(evidence_list) -> int:
    """
    FR-3.3: weighted fusion of evidence types into a 0-100 confidence score.
    Diminishing returns are applied so 3 thermal readings don't just triple-count.
    """
    if not evidence_list:
        return 0

    type_counts = {}
    for ev in evidence_list:
        type_counts[ev.type] = type_counts.get(ev.type, 0) + 1

    score = 0
    for ev_type, count in type_counts.items():
        base_weight = EVIDENCE_WEIGHTS.get(ev_type, 10)
        # diminishing returns: 1st reading full weight, each additional +30%
        score += base_weight + (count - 1) * (base_weight * 0.3)

    return min(int(round(score)), 100)


def fuse_evidence(db: Session, evidence: models.Evidence) -> models.SurvivorZone:
    """
    Main fusion entry point, called right after evidence is submitted.
    Implements FR-3.1 -> FR-3.4 in sequence, matching UC-2 in the SRS.
    """
    zone = find_or_create_zone(db, evidence.lat, evidence.lng)
    evidence.zone_id = zone.id
    db.commit()

    recent_evidence = get_recent_evidence_for_zone(db, zone.id)
    new_score = calculate_confidence(recent_evidence)

    zone.confidence_score = new_score
    zone.last_updated = datetime.datetime.utcnow()
    db.commit()
    db.refresh(zone)
    return zone
