import datetime
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import Base, get_db
from app.db import models

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db
client = TestClient(app)

LAT, LNG = 19.0, 73.0
METER_LAT = 1 / 111195.0


def post_evidence(ev_type, lat=LAT, lng=LNG, device=None):
    body = {"type": ev_type, "lat": lat, "lng": lng}
    if device:
        body["source_device_id"] = device
    return client.post("/api/evidence/", json=body)


def zones():
    return client.get("/api/evidence/zones").json()


class BlackBoxBVA(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

    def test_lat_boundary_valid_90(self):
        self.assertEqual(post_evidence("GPS", 90, 0).status_code, 200)

    def test_lat_boundary_invalid_90_1(self):
        self.assertEqual(post_evidence("GPS", 90.1, 0).status_code, 400)

    def test_lng_boundary_valid_minus_180(self):
        self.assertEqual(post_evidence("GPS", 0, -180).status_code, 200)

    def test_lng_boundary_invalid_180_1(self):
        self.assertEqual(post_evidence("GPS", 0, 180.1).status_code, 400)

    def test_radius_49m_joins_same_zone(self):
        post_evidence("GPS")
        post_evidence("GPS", LAT + 49 * METER_LAT)
        self.assertEqual(len(zones()), 1)

    def test_radius_51m_creates_new_zone(self):
        post_evidence("GPS")
        post_evidence("GPS", LAT + 51 * METER_LAT)
        self.assertEqual(len(zones()), 2)

    def test_score_progression(self):
        scores = []
        for t in ["GPS", "Sensor", "Visual", "Audio", "Thermal"]:
            post_evidence(t)
            scores.append(zones()[0]["confidence_score"])
        self.assertEqual(scores, [10, 25, 45, 70, 100])

    def test_alert_not_raised_at_70(self):
        for t in ["GPS", "Sensor", "Visual", "Audio"]:
            post_evidence(t)
        self.assertEqual(client.get("/api/alerts/").json(), [])

    def test_alert_critical_at_100(self):
        for t in ["GPS", "Sensor", "Visual", "Audio", "Thermal"]:
            post_evidence(t)
        alerts = client.get("/api/alerts/").json()
        self.assertEqual(alerts[0]["priority"], "Critical")

    def test_low_battery_boundary_19_percent(self):
        client.post("/api/devices/health", json={"id": "d19", "type": "ESP32", "battery_level": 19})
        post_evidence("Thermal", device="d19")
        self.assertEqual(zones()[0]["confidence_score"], 18)

    def test_battery_boundary_39_percent(self):
        client.post("/api/devices/health", json={"id": "d39", "type": "ESP32", "battery_level": 39})
        post_evidence("Thermal", device="d39")
        self.assertEqual(zones()[0]["confidence_score"], 26)

    def test_duplicate_active_task_returns_409(self):
        post_evidence("GPS")
        zone_id = zones()[0]["id"]
        team = client.post("/api/teams/", json={"team_name": "Alpha"}).json()
        first = client.post("/api/tasks/", json={"zone_id": zone_id, "team_id": team["id"], "priority": "High"})
        second = client.post("/api/tasks/", json={"zone_id": zone_id, "team_id": team["id"], "priority": "High"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)


if __name__ == "__main__":
    unittest.main(verbosity=2)
