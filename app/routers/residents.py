from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import admin_only, get_current_user
from ..models import (
    Announcement,
    AnnouncementComment,
    AnnouncementRead,
    Chore,
    Contribution,
    Expense,
    ParkingSpot,
    Resident,
)
from ..schemas import MessageOut, ResidentCreate, ResidentOut, ResidentUpdate
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
    current_user: Resident = Depends(admin_only),
):
    existing = db.scalar(select(Resident).where(Resident.dept_number == payload.dept_number))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un departamento con esa letra",
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
    current_user: Resident = Depends(admin_only),
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
                detail="Ya existe un departamento con esa letra",
            )

    if resident.id == current_user.id and values.get("role") not in (None, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes quitarte el rol de admin",
        )

    for field, value in values.items():
        setattr(resident, field, value)
    if pin:
        resident.pin_hash = hash_pin(pin)

    db.commit()
    db.refresh(resident)
    return resident_out(resident, paid_by_resident(db).get(resident.id, 0.0))


@router.delete("/{resident_id}", response_model=MessageOut)
def delete_resident(
    resident_id: int,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(admin_only),
):
    resident = db.get(Resident, resident_id)
    if resident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Residente no encontrado",
        )
    if resident.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes eliminar tu propio departamento",
        )

    announcement_ids = db.scalars(
        select(Announcement.id).where(Announcement.created_by == resident.id)
    ).all()
    if announcement_ids:
        db.execute(
            delete(AnnouncementRead).where(
                AnnouncementRead.announcement_id.in_(announcement_ids)
            )
        )
        db.execute(
            delete(AnnouncementComment).where(
                AnnouncementComment.announcement_id.in_(announcement_ids)
            )
        )
        db.execute(delete(Announcement).where(Announcement.id.in_(announcement_ids)))

    db.execute(delete(AnnouncementRead).where(AnnouncementRead.resident_id == resident.id))
    db.execute(
        delete(AnnouncementComment).where(AnnouncementComment.resident_id == resident.id)
    )

    db.execute(update(Chore).where(Chore.assigned_to == resident.id).values(assigned_to=None))
    db.execute(
        update(Chore)
        .where(Chore.completed_by == resident.id)
        .values(completed_by=current_user.id)
    )
    db.execute(update(Chore).where(Chore.created_by == resident.id).values(created_by=current_user.id))

    db.execute(
        update(Expense).where(Expense.created_by == resident.id).values(created_by=current_user.id)
    )
    db.execute(delete(Contribution).where(Contribution.resident_id == resident.id))
    db.execute(
        update(Contribution)
        .where(Contribution.approved_by == resident.id)
        .values(approved_by=current_user.id)
    )

    db.execute(
        update(ParkingSpot).where(ParkingSpot.owner_id == resident.id).values(owner_id=None)
    )
    db.execute(
        update(ParkingSpot)
        .where(ParkingSpot.borrower_id == resident.id)
        .values(borrower_id=None, status="Disponible", loan_until=None)
    )

    db.delete(resident)
    db.commit()
    return MessageOut(message="Departamento eliminado")
