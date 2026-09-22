"""
Task endpoints — FR-4.2 (assign), FR-4.3 (status update), FR-4.4 (no duplicates).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app import schemas

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("/", response_model=schemas.TaskOut)
def assign_task(payload: schemas.TaskCreate, db: Session = Depends(get_db)):
    zone = db.query(models.SurvivorZone).filter(models.SurvivorZone.id == payload.zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    # FR-4.4: block if this zone already has an active task
    active = (
        db.query(models.Task)
        .filter(
            models.Task.zone_id == payload.zone_id,
            models.Task.status.in_([models.TaskStatus.ASSIGNED, models.TaskStatus.IN_PROGRESS]),
        )
        .first()
    )
    if active:
        raise HTTPException(status_code=409, detail="Zone already has an active task")

    task = models.Task(
        zone_id=payload.zone_id,
        team_id=payload.team_id,
        priority=payload.priority,
        status=models.TaskStatus.ASSIGNED,
    )
    zone.status = models.ZoneStatus.ASSIGNED
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/", response_model=list[schemas.TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(models.Task).all()


@router.patch("/{task_id}/status", response_model=schemas.TaskOut)
def update_task_status(task_id: str, payload: schemas.TaskStatusUpdate, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = payload.status
    if payload.status == "Completed":
        # UC-8: mark zone searched, freeing it up / closing the loop
        zone = db.query(models.SurvivorZone).filter(models.SurvivorZone.id == task.zone_id).first()
        if zone:
            zone.status = models.ZoneStatus.SEARCHED
    db.commit()
    db.refresh(task)
    return task
