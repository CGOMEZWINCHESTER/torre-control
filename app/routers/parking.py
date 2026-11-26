from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import can_manage_parking, admin_only, get_current_user
from ..models import ParkingSpot, Resident
from ..schemas import (
    MessageOut,
    ParkingCreate,
    ParkingOut,
    ParkingUpdate,
    ResidentOut,
)
from ..services.residents import resident_out_map

router = APIRouter(prefix="/api/parking", tags=["parking"])


def _load_spot(spot_id: int, db: Session) -> ParkingSpot | None:
    return db.scalar(
        select(ParkingSpot)
        .options(joinedload(ParkingSpot.owner), joinedload(ParkingSpot.borrower))
        .execution_options(populate_existing=True)
        .where(ParkingSpot.id == spot_id)
    )


def _require_spot(spot_id: int, db: Session) -> ParkingSpot:
    spot = _load_spot(spot_id, db)
    if spot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lugar de estacionamiento no encontrado",
        )
    return spot


def _as_out(spot: ParkingSpot, residents: dict[int, ResidentOut]) -> ParkingOut:
    return ParkingOut.model_validate(spot).model_copy(
        update={
            "owner": residents.get(spot.owner_id),
            "borrower": residents.get(spot.borrower_id),
        }
    )


@router.get("", response_model=list[ParkingOut])
def list_parking(
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    spots = db.scalars(select(ParkingSpot).order_by(ParkingSpot.id.asc())).all()
    residents = resident_out_map(db)
    return [_as_out(spot, residents) for spot in spots]


@router.post("", response_model=ParkingOut, status_code=status.HTTP_201_CREATED)
def create_parking(
    payload: ParkingCreate,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(admin_only),
):
    values = payload.model_dump()
    if db.scalar(select(ParkingSpot).where(ParkingSpot.code == values["code"])) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El código del lugar ya existe",
        )
    spot = ParkingSpot(**values, status="Disponible")
    db.add(spot)
    db.commit()
    return _as_out(_require_spot(spot.id, db), resident_out_map(db))


@router.patch("/{spot_id}", response_model=ParkingOut)
def update_parking(
    spot_id: int,
    payload: ParkingUpdate,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(admin_only),
):
    spot = _require_spot(spot_id, db)
    values = payload.model_dump(exclude_unset=True)
    if "code" in values:
        duplicate = db.scalar(
            select(ParkingSpot).where(
                ParkingSpot.code == values["code"],
                ParkingSpot.id != spot.id,
            )
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El código del lugar ya existe",
            )
    for field, value in values.items():
        setattr(spot, field, value)
    db.commit()
    return _as_out(_require_spot(spot_id, db), resident_out_map(db))


@router.delete("/{spot_id}", response_model=MessageOut)
def delete_parking(
    spot_id: int,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(admin_only),
):
    spot = _require_spot(spot_id, db)
    db.delete(spot)
    db.commit()
    return MessageOut(message="Lugar eliminado")


@router.post("/{spot_id}/request", response_model=ParkingOut)
def request_parking(
    spot_id: int,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    spot = _require_spot(spot_id, db)
    spot.status = "Solicitado"
    spot.borrower_id = current_user.id
    db.commit()
    return _as_out(_require_spot(spot_id, db), resident_out_map(db))


@router.post("/{spot_id}/approve", response_model=ParkingOut)
def approve_parking(
    spot_id: int,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    spot = _require_spot(spot_id, db)
    if not can_manage_parking(current_user, spot):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el propietario o el admin puede aprobar el préstamo",
        )
    spot.status = "Prestado"
    db.commit()
    return _as_out(_require_spot(spot_id, db), resident_out_map(db))


@router.post("/{spot_id}/release", response_model=ParkingOut)
def release_parking(
    spot_id: int,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    spot = _require_spot(spot_id, db)
    if not can_manage_parking(current_user, spot):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el propietario o el admin puede liberar el lugar",
        )
    spot.status = "Disponible"
    spot.borrower_id = None
    spot.note = None
    spot.loan_until = None
    db.commit()
    return _as_out(_require_spot(spot_id, db), resident_out_map(db))
