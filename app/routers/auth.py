from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Resident
from ..schemas import MessageOut, PINLogin, ResidentOut, UserProfile
from ..services.residents import paid_by_resident, resident_out
from ..services.security import create_session_token, verify_pin

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.get("/profiles", response_model=list[UserProfile])
def list_profiles(db: Session = Depends(get_db)):
    return db.scalars(select(Resident).order_by(Resident.dept_number.asc())).all()


@router.post("/login", response_model=ResidentOut)
def login(payload: PINLogin, response: Response, db: Session = Depends(get_db)):
    resident = db.scalar(
        select(Resident).where(Resident.dept_number == payload.dept_number)
    )
    if resident is None or not verify_pin(payload.pin, resident.pin_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Departamento o PIN incorrecto",
        )

    response.set_cookie(
        key=settings.session_cookie_name,
        value=create_session_token(resident.id),
        max_age=settings.session_max_age,
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies,
        path="/",
    )
    return resident_out(resident, paid_by_resident(db).get(resident.id, 0.0))


@router.post("/logout", response_model=MessageOut)
def logout(response: Response):
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        samesite="lax",
        secure=settings.secure_cookies,
        httponly=True,
    )
    return MessageOut(message="Sesión cerrada")


@router.get("/me", response_model=ResidentOut)
def me(
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    return resident_out(current_user, paid_by_resident(db).get(current_user.id, 0.0))
