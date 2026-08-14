"""
Gestión del equipo: ver miembros actuales e invitaciones pendientes,
invitar a un compañero por email. Cada usuario pertenece exactamente a
una organización en esta primera versión (la personal, o la que aceptó
por invitación); el modelo de datos soporta más de una en el futuro sin
cambios de esquema.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    Membership, Organization, OrganizationInvitation, OrganizationRole, User,
)
from app.schemas.schemas import InviteRequest, MemberOut, OrganizationOut
from app.services.organizations import count_organization_members

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


def _get_current_membership(db: Session, user_id: str) -> Membership:
    membership = db.query(Membership).filter(Membership.user_id == user_id).first()
    if not membership:
        raise HTTPException(500, "El usuario no pertenece a ninguna organización (estado inconsistente)")
    return membership


@router.get("/me", response_model=OrganizationOut)
def get_my_organization(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    membership = _get_current_membership(db, current_user.id)
    org = db.query(Organization).filter(Organization.id == membership.organization_id).first()

    members: list[MemberOut] = []
    for m in db.query(Membership).filter(Membership.organization_id == org.id).all():
        u = db.query(User).filter(User.id == m.user_id).first()
        members.append(MemberOut(user_id=m.user_id, email=u.email, role=m.role, status="activo"))

    pending = db.query(OrganizationInvitation).filter(
        OrganizationInvitation.organization_id == org.id,
        OrganizationInvitation.accepted_at.is_(None),
    ).all()
    for inv in pending:
        members.append(MemberOut(
            user_id="", email=inv.email, role=inv.role, status="invitación pendiente",
        ))

    return OrganizationOut(id=org.id, name=org.name, my_role=membership.role, members=members)


@router.post("/invite", response_model=MemberOut)
def invite_teammate(payload: InviteRequest, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    membership = _get_current_membership(db, current_user.id)
    if membership.role not in (OrganizationRole.owner, OrganizationRole.admin):
        raise HTTPException(403, "Solo el propietario o un administrador puede invitar")

    role = OrganizationRole.admin if payload.role == "admin" else OrganizationRole.member
    email = payload.email.lower()

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        already_member = db.query(Membership).filter(
            Membership.organization_id == membership.organization_id,
            Membership.user_id == existing_user.id,
        ).first()
        if already_member:
            raise HTTPException(400, "Ese usuario ya es miembro del equipo")

        # Un usuario, en esta primera versión, solo pertenece a una
        # organización a la vez. Si la suya actual tiene otros miembros
        # (es un equipo de verdad, no su espacio personal en solitario),
        # no se puede mover automáticamente — evitamos dejarlo en dos
        # equipos a la vez de forma ambigua.
        current_memberships = db.query(Membership).filter(Membership.user_id == existing_user.id).all()
        for cm in current_memberships:
            if count_organization_members(db, cm.organization_id) > 1:
                raise HTTPException(
                    400,
                    "Ese usuario ya forma parte de otro equipo con más miembros. "
                    "Debe salir de ese equipo antes de poder unirse a uno nuevo.",
                )

        # Su organización actual era solo su espacio personal en solitario:
        # se retira de ahí y se une al nuevo equipo.
        for cm in current_memberships:
            db.delete(cm)

        new_membership = Membership(
            organization_id=membership.organization_id, user_id=existing_user.id, role=role,
        )
        db.add(new_membership)
        db.commit()
        return MemberOut(user_id=existing_user.id, email=email, role=role, status="activo")

    existing_invite = db.query(OrganizationInvitation).filter(
        OrganizationInvitation.organization_id == membership.organization_id,
        OrganizationInvitation.email == email,
        OrganizationInvitation.accepted_at.is_(None),
    ).first()
    if existing_invite:
        raise HTTPException(400, "Ya hay una invitación pendiente para ese email")

    invitation = OrganizationInvitation(
        organization_id=membership.organization_id, email=email, role=role,
        invited_by_user_id=current_user.id,
    )
    db.add(invitation)
    db.commit()
    return MemberOut(user_id="", email=email, role=role, status="invitación pendiente")
