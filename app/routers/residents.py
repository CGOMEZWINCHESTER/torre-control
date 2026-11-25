from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import committee_only, get_current_user
from ..models import Resident
from ..schemas import ResidentCreate, ResidentOut, ResidentUpdate
from ..services.residents import avatar_for, paid_by_resident, resident_out, resident_out_map
from ..services.security import hash_pin

router = APIRouter(prefix="/api/residents", tags=["residents"])


@router.get("", response_model=list[ResidentOut])
def list_residents(
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    residents = db.scalars(select(Resident).order_by(Resident.dept_number.asc())).all()
    residents_out = resident_out_map(db, list(residents))
    return [residents_out[resident.id] for resident in residents]


@router.post("", response_model=ResidentOut, status_code=status.HTTP_201_CREATED)
def create_resident(
    payload: ResidentCreate,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(committee_only),
):
    existing = db.scalar(select(Resident).where(Resident.dept_number == payload.dept_number))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un departamento con ese número",
        )

    values = payload.model_dump(exclude={"pin"})
    avatar_color, avatar_icon = avatar_for(values["name"], values["dept_number"])
    resident = Resident(
        **values,
        avatar_color=avatar_color,
        avatar_icon=avatar_icon,
        pin_hash=hash_pin(payload.pin),
    )
    db.add(resident)
    db.commit()
    db.refresh(resident)
    return resident_out(resident, 0.0)


@router.patch("/{resident_id}", response_model=ResidentOut)
def update_resident(
    resident_id: int,
    payload: ResidentUpdate,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(committee_only),
):
    resident = db.get(Resident, resident_id)
    if resident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Residente no encontrado",
        )

    values = payload.model_dump(exclude_unset=True)
    pin = values.pop("pin", None)

    if "dept_number" in values and values["dept_number"] != resident.dept_number:
        existing = db.scalar(
            select(Resident).where(Resident.dept_number == values["dept_number"])
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un departamento con ese número",
            )

    if resident.id == current_user.id and values.get("role") not in (None, "committee"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes quitarte el rol de comité",
        )

    for field, value in values.items():
        setattr(resident, field, value)
    if pin:
        resident.pin_hash = hash_pin(pin)

    db.commit()
    db.refresh(resident)
    return resident_out(resident, paid_by_resident(db).get(resident.id, 0.0))
