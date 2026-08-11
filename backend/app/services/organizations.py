"""
Resuelve qué usuarios comparten organización con un usuario dado. Es el
punto único que reemplaza las comprobaciones "== current_user.id" por
"pertenece al mismo equipo", sin tocar el esquema de las tablas de datos
(businesses, prospecting_profiles, etc.) — solo cambia CÓMO se filtra.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.models import Membership, Organization, OrganizationInvitation, OrganizationRole


def get_teammate_user_ids(db: Session, user_id: str) -> list[str]:
    """
    Devuelve los IDs de todos los usuarios que comparten AL MENOS UNA
    organización con `user_id`, incluyéndolo a él mismo. Si el usuario no
    tiene ninguna membresía (no debería pasar tras el registro normal,
    pero es un fallback seguro), devuelve solo su propio ID — igual que
    el comportamiento anterior a esta funcionalidad.
    """
    org_ids = [
        m.organization_id for m in
        db.query(Membership).filter(Membership.user_id == user_id).all()
    ]
    if not org_ids:
        return [user_id]

    teammate_ids = {
        m.user_id for m in
        db.query(Membership).filter(Membership.organization_id.in_(org_ids)).all()
    }
    teammate_ids.add(user_id)
    return list(teammate_ids)


def get_user_role(db: Session, user_id: str, organization_id: str) -> OrganizationRole | None:
    m = db.query(Membership).filter(
        Membership.user_id == user_id, Membership.organization_id == organization_id
    ).first()
    return m.role if m else None


def count_organization_members(db: Session, organization_id: str) -> int:
    return db.query(Membership).filter(Membership.organization_id == organization_id).count()


def create_personal_organization(db: Session, user_id: str, name_hint: str) -> Organization:
    org = Organization(name=f"Organización de {name_hint}")
    db.add(org)
    db.flush()
    db.add(Membership(organization_id=org.id, user_id=user_id, role=OrganizationRole.owner))
    return org


def resolve_signup_organization(db: Session, user_id: str, email: str) -> Organization:
    """
    Se llama justo después de crear un usuario nuevo. Si había una
    invitación pendiente para ese email, se une a esa organización con
    el rol invitado. Si no, se le crea una organización personal (así
    todo usuario existente antes de esta funcionalidad sigue teniendo
    exactamente el mismo comportamiento: su propio espacio aislado).
    """
    invitation = db.query(OrganizationInvitation).filter(
        OrganizationInvitation.email == email.lower(),
        OrganizationInvitation.accepted_at.is_(None),
    ).first()

    if invitation:
        db.add(Membership(
            organization_id=invitation.organization_id, user_id=user_id, role=invitation.role,
        ))
        invitation.accepted_at = datetime.utcnow()
        db.flush()
        return db.query(Organization).filter(Organization.id == invitation.organization_id).first()

    return create_personal_organization(db, user_id, email)
