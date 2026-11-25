from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import Chore, ParkingSpot, Resident
from .schemas import Role
from .services.security import read_session_token

settings = get_settings()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Resident:
    token = request.cookies.get(settings.session_cookie_name)
    user_id = read_session_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inicia sesión para continuar",
        )

    user = db.get(Resident, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión no válida",
        )
    return user


def require_roles(*allowed: Role):
    def dependency(current_user: Resident = Depends(get_current_user)) -> Resident:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para esta acción",
            )
        return current_user

    return dependency


committee_only = require_roles("committee")


def can_manage_chore(user: Resident, chore: Chore) -> bool:
    return user.role == "committee" or chore.assigned_to == user.id


def can_manage_parking(user: Resident, spot: ParkingSpot) -> bool:
    return user.role == "committee" or spot.owner_id == user.id
