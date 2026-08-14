from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import ProspectingProfile, User
from app.schemas.schemas import ProfileCreate, ProfileOut
from app.services.organizations import get_teammate_user_ids

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.post("", response_model=ProfileOut)
def create_profile(payload: ProfileCreate, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    # El perfil se crea a nombre de quien lo crea, pero es visible para
    # todo el equipo (ver list_profiles/get_profile más abajo).
    profile = ProspectingProfile(user_id=current_user.id, **payload.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("", response_model=list[ProfileOut])
def list_profiles(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    teammate_ids = get_teammate_user_ids(db, current_user.id)
    return db.query(ProspectingProfile).filter(ProspectingProfile.user_id.in_(teammate_ids)).all()


@router.get("/{profile_id}", response_model=ProfileOut)
def get_profile(profile_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    teammate_ids = get_teammate_user_ids(db, current_user.id)
    profile = db.query(ProspectingProfile).filter(
        ProspectingProfile.id == profile_id, ProspectingProfile.user_id.in_(teammate_ids)
    ).first()
    if not profile:
        raise HTTPException(404, "Perfil no encontrado")
    return profile
