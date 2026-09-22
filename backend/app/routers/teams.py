"""
Team endpoints — FR-4.1 (live team location for the dashboard).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app import schemas

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.post("/", response_model=schemas.TeamOut)
def create_team(payload: schemas.TeamCreate, db: Session = Depends(get_db)):
    team = models.Team(team_name=payload.team_name)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.get("/", response_model=list[schemas.TeamOut])
def list_teams(db: Session = Depends(get_db)):
    return db.query(models.Team).all()


@router.patch("/{team_id}/location", response_model=schemas.TeamOut)
def update_location(team_id: str, payload: schemas.TeamLocationUpdate, db: Session = Depends(get_db)):
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    team.current_lat = payload.lat
    team.current_lng = payload.lng
    db.commit()
    db.refresh(team)
    return team
