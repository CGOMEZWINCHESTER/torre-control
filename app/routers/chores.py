from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import can_manage_chore, admin_only, get_current_user
from ..models import Chore, Resident
from ..schemas import (
    ChoreComplete,
    ChoreCreate,
    ChoreFilter,
    ChoreOut,
    ChoreUpdate,
    MessageOut,
    ResidentOut,
)
from ..services.images import validate_image_data_url
from ..services.recurrence import next_due_date
from ..services.residents import resident_out_map

router = APIRouter(prefix="/api/chores", tags=["chores"])


def _load_chore(chore_id: int, db: Session) -> Chore | None:
    return db.scalar(
        select(Chore)
        .options(
            joinedload(Chore.assignee),
            joinedload(Chore.creator),
            joinedload(Chore.completer),
        )
        .execution_options(populate_existing=True)
        .where(Chore.id == chore_id)
    )


def _require_chore(chore_id: int, db: Session) -> Chore:
    chore = _load_chore(chore_id, db)
    if chore is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada",
        )
    return chore


def _as_out(chore: Chore, residents: dict[int, ResidentOut]) -> ChoreOut:
    return ChoreOut.model_validate(chore).model_copy(
        update={
            "assignee": residents.get(chore.assigned_to),
            "creator": residents[chore.created_by],
            "completer": residents.get(chore.completed_by),
        }
    )


def _next_assignee(db: Session, chore: Chore) -> int | None:
    residents = db.scalars(
        select(Resident).order_by(Resident.dept_number.asc(), Resident.id.asc())
    ).all()
    if not residents:
        return None

    resident_ids = [resident.id for resident in residents]
    if chore.assigned_to not in resident_ids:
        return resident_ids[0]
    index = resident_ids.index(chore.assigned_to)
    return resident_ids[(index + 1) % len(resident_ids)]


@router.get("", response_model=list[ChoreOut])
def list_chores(
    filter: ChoreFilter = Query(default="all"),
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    query = select(Chore).options(
        joinedload(Chore.assignee),
        joinedload(Chore.creator),
        joinedload(Chore.completer),
    )
    if filter == "mine":
        query = query.where(Chore.assigned_to == current_user.id, Chore.is_completed.is_(False))
    elif filter == "pending":
        query = query.where(Chore.is_completed.is_(False))
    elif filter == "completed":
        query = query.where(Chore.is_completed.is_(True))

    chores = db.scalars(query.order_by(Chore.created_at.desc(), Chore.id.desc())).all()
    residents = resident_out_map(db)
    return [_as_out(chore, residents) for chore in chores]


@router.post("", response_model=ChoreOut, status_code=status.HTTP_201_CREATED)
def create_chore(
    payload: ChoreCreate,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(admin_only),
):
    chore = Chore(**payload.model_dump(), created_by=current_user.id)
    db.add(chore)
    db.commit()
    return _as_out(_require_chore(chore.id, db), resident_out_map(db))


@router.patch("/{chore_id}", response_model=ChoreOut)
def update_chore(
    chore_id: int,
    payload: ChoreUpdate,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(admin_only),
):
    chore = _require_chore(chore_id, db)
    values = payload.model_dump(exclude_unset=True)
    if "evidence_url" in values:
        values["evidence_url"] = validate_image_data_url(values["evidence_url"])
    for field, value in values.items():
        setattr(chore, field, value)
    db.commit()
    return _as_out(_require_chore(chore_id, db), resident_out_map(db))


@router.delete("/{chore_id}", response_model=MessageOut)
def delete_chore(
    chore_id: int,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(admin_only),
):
    chore = _require_chore(chore_id, db)
    db.delete(chore)
    db.commit()
    return MessageOut(message="Tarea eliminada")


@router.post("/{chore_id}/complete", response_model=ChoreOut)
def complete_chore(
    chore_id: int,
    payload: ChoreComplete,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    chore = _require_chore(chore_id, db)
    if not can_manage_chore(current_user, chore):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para completar esta tarea",
        )

    evidence_url = validate_image_data_url(payload.evidence_url)

    if not chore.is_completed:
        chore.is_completed = True
        chore.completed_at = datetime.now(timezone.utc)
        chore.completed_by = current_user.id

        if chore.frequency != "Única":
            next_chore = Chore(
                title=chore.title,
                description=chore.description,
                area=chore.area,
                frequency=chore.frequency,
                due_date=next_due_date(chore.due_date, chore.frequency),
                assigned_to=_next_assignee(db, chore),
                created_by=chore.created_by,
            )
            db.add(next_chore)
            db.flush()
            chore.next_chore_id = next_chore.id

    if payload.model_fields_set and "evidence_url" in payload.model_fields_set:
        chore.evidence_url = evidence_url

    db.commit()
    return _as_out(_require_chore(chore_id, db), resident_out_map(db))


@router.post("/{chore_id}/reopen", response_model=ChoreOut)
def reopen_chore(
    chore_id: int,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    chore = _require_chore(chore_id, db)
    if not can_manage_chore(current_user, chore):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para reabrir esta tarea",
        )

    chore.is_completed = False
    chore.completed_at = None
    chore.completed_by = None
    chore.evidence_url = None
    db.commit()
    return _as_out(_require_chore(chore_id, db), resident_out_map(db))
