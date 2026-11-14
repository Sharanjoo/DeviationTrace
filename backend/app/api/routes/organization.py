"""Company profile and members.

Roles (enforced in app.core.security):
- admin: in charge; manages members, roles and the company profile
- member: does the audit work
- viewer: read-only
"""

import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.onboarding.scope_templates import SCOPE_TEMPLATES
from app.core.security import CurrentOrg, get_current_org, hash_password, require_admin
from app.database import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import (
    MemberCreate,
    MemberCreated,
    MemberOut,
    MemberUpdate,
    OrgProfileOut,
    OrgProfileUpdate,
)

router = APIRouter(prefix="/org", tags=["organization"])

_ROLE_ORDER = {"admin": 0, "member": 1, "viewer": 2}


def _active_members(db: Session, org_id: uuid.UUID) -> list[User]:
    members = db.query(User).filter(User.org_id == org_id, User.is_active.is_(True)).all()
    return sorted(members, key=lambda u: (_ROLE_ORDER.get(u.role, 9), (u.full_name or u.email).lower()))


def _profile(db: Session, current: CurrentOrg) -> OrgProfileOut:
    org = db.get(Organization, current.org_id)
    template = SCOPE_TEMPLATES.get(org.scope_category) if org.scope_category else None
    return OrgProfileOut(
        id=org.id,
        name=org.name,
        industry=org.industry,
        created_at=org.created_at,
        onboarded_at=org.onboarded_at,
        scope_label=template.label if template else None,
        member_count=len(_active_members(db, org.id)),
        you=MemberOut.model_validate(db.get(User, current.user_id)),
    )


def _get_member(db: Session, org_id: uuid.UUID, member_id: uuid.UUID) -> User:
    user = db.get(User, member_id)
    if user is None or user.org_id != org_id or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return user


def _ensure_another_admin(db: Session, org_id: uuid.UUID, leaving: User) -> None:
    """An organization must always keep at least one admin."""
    admins = [u for u in _active_members(db, org_id) if u.role == "admin"]
    if leaving.role == "admin" and len(admins) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The organization needs at least one admin. Make someone else an admin first.",
        )


@router.get("/profile", response_model=OrgProfileOut)
def get_profile(current: CurrentOrg = Depends(get_current_org), db: Session = Depends(get_db)) -> OrgProfileOut:
    return _profile(db, current)


@router.patch("/profile", response_model=OrgProfileOut)
def update_profile(
    payload: OrgProfileUpdate, current: CurrentOrg = Depends(require_admin), db: Session = Depends(get_db)
) -> OrgProfileOut:
    db.get(Organization, current.org_id).name = payload.name
    db.commit()
    return _profile(db, current)


@router.get("/members", response_model=list[MemberOut])
def list_members(current: CurrentOrg = Depends(get_current_org), db: Session = Depends(get_db)) -> list[User]:
    return _active_members(db, current.org_id)


@router.post("/members", response_model=MemberCreated, status_code=status.HTTP_201_CREATED)
def add_member(
    payload: MemberCreate, current: CurrentOrg = Depends(require_admin), db: Session = Depends(get_db)
) -> MemberCreated:
    """Give someone access. They sign in with their email and the temporary
    password returned here (shown once)."""
    temporary_password = secrets.token_urlsafe(9)
    user = User(
        org_id=current.org_id,
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
        hashed_password=hash_password(temporary_password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That email already has an account") from exc
    db.refresh(user)
    return MemberCreated(member=MemberOut.model_validate(user), temporary_password=temporary_password)


@router.patch("/members/{member_id}", response_model=MemberOut)
def update_member(
    member_id: uuid.UUID,
    payload: MemberUpdate,
    current: CurrentOrg = Depends(get_current_org),
    db: Session = Depends(get_db),
) -> User:
    """Admins can change anyone's name or role; everyone else can only
    change their own name."""
    member = _get_member(db, current.org_id, member_id)
    is_self = member.id == current.user_id
    if current.role != "admin" and (not is_self or payload.role is not None):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only an admin can change other members")

    if payload.role is not None and payload.role != member.role:
        if member.role == "admin":
            _ensure_another_admin(db, current.org_id, member)
        member.role = payload.role
    if payload.full_name is not None:
        member.full_name = payload.full_name.strip() or None
    db.commit()
    db.refresh(member)
    return member


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    member_id: uuid.UUID, current: CurrentOrg = Depends(require_admin), db: Session = Depends(get_db)
) -> None:
    """Remove someone's access. Their account is deactivated (not deleted),
    so their past review decisions keep their name."""
    member = _get_member(db, current.org_id, member_id)
    if member.id == current.user_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You can't remove yourself")
    _ensure_another_admin(db, current.org_id, member)
    member.is_active = False
    db.commit()
