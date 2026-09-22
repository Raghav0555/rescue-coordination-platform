"""
Entry point for the prototype backend.
Run with: uvicorn app.main:app --reload --port 8000
Interactive API docs at: http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import engine, Base
from app.routers import auth, evidence, teams, tasks, alerts

# Creates all tables on startup (fine for a prototype; use Alembic migrations
# for anything beyond this, as noted in the SRS Section 7).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Rescue Evidence Fusion & Coordination Platform (Prototype)",
    description="Prototype backend implementing the High-priority FRs from Sprint 1.",
    version="0.1.0",
)

# Wide-open CORS since this is a local prototype — lock down before deploying.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(evidence.router)
app.include_router(teams.router)
app.include_router(tasks.router)
app.include_router(alerts.router)


@app.get("/")
def root():
    return {"status": "ok", "message": "Rescue Coordination Platform API is running"}
