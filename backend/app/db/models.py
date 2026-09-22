"""
SQLAlchemy models — these map directly to the entities in the SRS Data
Dictionary (Section 7): User, Team, Evidence, SurvivorZone, Task, Alert.
"""
import uuid
import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from .database import Base


def gen_id():
    return str(uuid.uuid4())[:8]


class RoleEnum(str, enum.Enum):
    FIELD_RESPONDER = "FieldResponder"
    DRONE_OPERATOR = "DroneOperator"
    SENSOR_OPERATOR = "SensorOperator"
    DOG_HANDLER = "DogHandler"
    COORDINATOR = "Coordinator"
    ADMIN = "Admin"


class EvidenceType(str, enum.Enum):
    THERMAL = "Thermal"
    GPS = "GPS"
    AUDIO = "Audio"
    VISUAL = "Visual"
    SENSOR = "Sensor"


class TaskStatus(str, enum.Enum):
    UNASSIGNED = "Unassigned"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"


class ZoneStatus(str, enum.Enum):
    UNSEARCHED = "Unsearched"
    ASSIGNED = "Assigned"
    SEARCHED = "Searched"


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)
    contact_number = Column(String)
    password_hash = Column(String, nullable=False)
    team_id = Column(String, ForeignKey("teams.id"), nullable=True)

    team = relationship("Team", back_populates="members")


class Team(Base):
    __tablename__ = "teams"
    id = Column(String, primary_key=True, default=gen_id)
    team_name = Column(String, nullable=False)
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    status = Column(String, default="Available")  # Available | Assigned | Unavailable

    members = relationship("User", back_populates="team")
    tasks = relationship("Task", back_populates="team")


class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(String, primary_key=True, default=gen_id)
    type = Column(Enum(EvidenceType), nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    source_device_id = Column(String)
    zone_id = Column(String, ForeignKey("survivor_zones.id"), nullable=True)
    note = Column(String, nullable=True)

    zone = relationship("SurvivorZone", back_populates="evidence_items")


class SurvivorZone(Base):
    __tablename__ = "survivor_zones"
    id = Column(String, primary_key=True, default=gen_id)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    confidence_score = Column(Integer, default=0)
    status = Column(Enum(ZoneStatus), default=ZoneStatus.UNSEARCHED)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)

    evidence_items = relationship("Evidence", back_populates="zone")
    tasks = relationship("Task", back_populates="zone")
    alerts = relationship("Alert", back_populates="zone")
    def __repr__(self):
        return f"<SurvivorZone {self.id} score={self.confidence_score}>"


class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True, default=gen_id)
    zone_id = Column(String, ForeignKey("survivor_zones.id"))
    team_id = Column(String, ForeignKey("teams.id"), nullable=True)
    priority = Column(String, default="Medium")  # Low | Medium | High | Critical
    status = Column(Enum(TaskStatus), default=TaskStatus.UNASSIGNED)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    zone = relationship("SurvivorZone", back_populates="tasks")
    team = relationship("Team", back_populates="tasks")


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(String, primary_key=True, default=gen_id)
    zone_id = Column(String, ForeignKey("survivor_zones.id"))
    trigger_score = Column(Integer)
    priority = Column(String, default="High")
    acknowledged = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    zone = relationship("SurvivorZone", back_populates="alerts")


class Device(Base):
    """
    Implements the Data Dictionary's Device entity (SRS Section 7).
    Tracked separately from Evidence.source_device_id so the Fusion Engine
    can look up a device's current health when weighting its evidence
    (FR-3.5), rather than trusting every submission equally.
    """
    __tablename__ = "devices"
    id = Column(String, primary_key=True)  # matches Evidence.source_device_id, e.g. "drone-1"
    type = Column(String, default="MobileApp")  # ESP32Node | RaspberryPiNode | DroneSensor | MobileApp
    battery_level = Column(Integer, default=100)  # 0-100
    last_calibration = Column(DateTime, default=datetime.datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.datetime.utcnow)