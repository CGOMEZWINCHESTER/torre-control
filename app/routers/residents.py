from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import committee_only, get_current_user
from ..models import Resident
from ..schemas import ResidentOut, ResidentUpdate
from ..services.residents import paid_by_resident, resident_out, resident_out_map

router = APIRouter(prefix="/api/residents", tags=["residents"])


@router.get("", response_model=list[ResidentOut])
def list_residents(
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    residents = db.scalars(select(Resident).order_by(Resident.dept_number.asc())).all()
    residents_out = resident_out_map(db, list(residents))
    return [residents_out[resident.id] for resident in residents]


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

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(resident, field, value)
    db.commit()
    db.refresh(resident)
    return resident_out(resident, paid_by_resident(db).get(resident.id, 0.0))
