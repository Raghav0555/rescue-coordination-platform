"""
Database connection setup for the prototype.
Uses SQLite instead of PostGIS/Postgres to keep the prototype dependency-free
and runnable on any machine without a separate DB server. The schema mirrors
what's described in the SRS Data Dictionary (Section 7) — swapping this out
for PostGIS later just means changing DATABASE_URL and using GeoAlchemy2
columns instead of plain lat/lng floats.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./rescue_platform.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
