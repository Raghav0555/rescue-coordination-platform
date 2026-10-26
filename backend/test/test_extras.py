import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import Base, get_db

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


class ExtraRuleTests(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    def zone_and_team(self):
        client.post("/api/evidence/", json={"type": "Thermal", "lat": 19.0, "lng": 73.0})
        zone = client.get("/api/evidence/zones").json()[0]
        team = client.post("/api/teams/", json={"team_name": "Alpha"}).json()
        return zone, team

    def test_unknown_evidence_type_rejected(self):
        r = client.post("/api/evidence/", json={"type": "Bogus", "lat": 19.0, "lng": 73.0})
        self.assertEqual(r.status_code, 400)

    def test_task_for_unknown_team_returns_404(self):
        zone, _ = self.zone_and_team()
        r = client.post("/api/tasks/", json={"zone_id": zone["id"], "team_id": "nope"})
        self.assertEqual(r.status_code, 404)

    def test_invalid_task_status_rejected(self):
        zone, team = self.zone_and_team()
        task = client.post("/api/tasks/", json={"zone_id": zone["id"], "team_id": team["id"]}).json()
        r = client.patch(f"/api/tasks/{task['id']}/status", json={"status": "Banana"})
        self.assertEqual(r.status_code, 400)

    def test_completed_task_marks_zone_searched_and_frees_team(self):
        zone, team = self.zone_and_team()
        task = client.post("/api/tasks/", json={"zone_id": zone["id"], "team_id": team["id"]}).json()
        client.patch(f"/api/tasks/{task['id']}/status", json={"status": "Completed"})
        self.assertEqual(client.get("/api/evidence/zones").json()[0]["status"], "Searched")
        self.assertEqual(client.get("/api/teams/").json()[0]["status"], "Available")

    def test_battery_out_of_range_rejected(self):
        r = client.post("/api/devices/health", json={"id": "d1", "battery_level": 150})
        self.assertEqual(r.status_code, 400)

    def test_report_endpoints_are_reachable(self):
        self.zone_and_team()
        js = client.get("/api/reports/summary")
        csv = client.get("/api/reports/summary.csv")
        self.assertEqual(js.status_code, 200)
        self.assertEqual(js.json()[0]["evidence_count"], 1)
        self.assertEqual(csv.status_code, 200)
        self.assertTrue(csv.text.startswith("zone_id"))


if __name__ == "__main__":
    unittest.main()
