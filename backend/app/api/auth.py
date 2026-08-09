from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.models.models import User
from app.schemas.schemas import UserCreate, UserOut, Token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
@limiter.limit("3/hour")
def register(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Ese email ya está registrado")
    user = User(email=payload.email, hashed_password=hash_password(payload.password), full_name=payload.full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(401, "Credenciales incorrectas")
    token = create_access_token({"sub": user.id})
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
