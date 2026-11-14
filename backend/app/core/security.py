import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.user import User

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_access_token(org_id: uuid.UUID, user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"org_id": str(org_id), "user_id": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


ROLES = ("admin", "member", "viewer")
_READ_ONLY_METHODS = {"GET", "HEAD", "OPTIONS"}


class CurrentOrg:
    def __init__(self, org_id: uuid.UUID, user_id: uuid.UUID, role: str = "member"):
        self.org_id = org_id
        self.user_id = user_id
        self.role = role


def get_current_org(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentOrg:
    """Authenticate the request and apply the user's role. Checked against
    the database on every request, so a role change or removal takes effect
    immediately rather than when the token expires. Viewers are read-only:
    any request that could change data is refused here, for every route."""
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        org_id, user_id = uuid.UUID(payload["org_id"]), uuid.UUID(payload["user_id"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    user = db.get(User, user_id)
    if user is None or user.org_id != org_id or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This account no longer has access")
    if user.role == "viewer" and request.method not in _READ_ONLY_METHODS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You have view-only access")
    return CurrentOrg(org_id=org_id, user_id=user_id, role=user.role)


def require_admin(current: CurrentOrg = Depends(get_current_org)) -> CurrentOrg:
    if current.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only an admin of this organization can do that"
        )
    return current
