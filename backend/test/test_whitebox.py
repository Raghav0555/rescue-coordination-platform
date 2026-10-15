import datetime
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db import models
from app.services import fusion_engine as fe


def new_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def add_device(db, battery, days_old):
    d = models.Device(id="dev", type="ESP32", battery_level=battery)
    d.last_calibration = datetime.datetime.utcnow() - datetime.timedelta(days=days_old)
    db.add(d)
    db.commit()


class DeviceHealthPaths(unittest.TestCase):
    def setUp(self):
        self.db = new_session()

    def test_path1_no_device_id(self):
        self.assertEqual(fe.get_device_health_factor(self.db, None), 1.0)

    def test_path2_unknown_device(self):
        self.assertEqual(fe.get_device_health_factor(self.db, "ghost"), 1.0)

    def test_path3_battery_low_calibration_fresh(self):
        add_device(self.db, 19, 0)
        self.assertEqual(fe.get_device_health_factor(self.db, "dev"), 0.6)

    def test_path4_battery_low_calibration_stale(self):
        add_device(self.db, 19, 31)
        self.assertEqual(fe.get_device_health_factor(self.db, "dev"), 0.48)

    def test_path5_battery_medium_calibration_fresh(self):
        add_device(self.db, 39, 0)
        self.assertEqual(fe.get_device_health_factor(self.db, "dev"), 0.85)

    def test_path6_battery_medium_calibration_stale(self):
        add_device(self.db, 39, 31)
        self.assertEqual(fe.get_device_health_factor(self.db, "dev"), 0.68)

    def test_path7_battery_good_calibration_fresh(self):
        add_device(self.db, 80, 0)
        self.assertEqual(fe.get_device_health_factor(self.db, "dev"), 1.0)

    def test_path8_battery_good_calibration_stale(self):
        add_device(self.db, 80, 31)
        self.assertEqual(fe.get_device_health_factor(self.db, "dev"), 0.8)


class HaversineAndScore(unittest.TestCase):
    def test_same_point_is_zero(self):
        self.assertEqual(fe.haversine_distance_m(19.0, 73.0, 19.0, 73.0), 0)

    def test_known_distance(self):
        d = fe.haversine_distance_m(0, 0, 0, 0.001)
        self.assertAlmostEqual(d, 111.19, delta=0.5)

    def test_empty_evidence_scores_zero(self):
        self.assertEqual(fe.calculate_confidence(new_session(), []), 0)

    def test_score_capped_at_100(self):
        db = new_session()
        evs = [models.Evidence(type="Thermal", lat=0, lng=0) for _ in range(10)]
        self.assertEqual(fe.calculate_confidence(db, evs), 100)

    def test_repeat_same_type_counts_30_percent(self):
        db = new_session()
        evs = [models.Evidence(type="Thermal", lat=0, lng=0) for _ in range(2)]
        self.assertEqual(fe.calculate_confidence(db, evs), 39)


if __name__ == "__main__":
    unittest.main(verbosity=2)
