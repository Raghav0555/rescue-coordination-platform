"""
Auth endpoints — FR-1.1 (register), FR-1.2 (login).
2FA/OTP is noted in the SRS but omitted here to keep the prototype runnable
without an SMS/email provider — see security.py docstring.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app import schemas
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.name == user_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    user = models.User(
        name=user_in.name,
        role=user_in.role,
        contact_number=user_in.contact_number,
        password_hash=hash_password(user_in.password),
        team_id=user_in.team_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.name == payload.name).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.id, "role": user.role})
    return {"access_token": token, "role": user.role}
