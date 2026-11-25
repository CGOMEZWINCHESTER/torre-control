from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import committee_only, get_current_user
from ..models import Announcement, AnnouncementComment, AnnouncementRead, Resident
from ..schemas import (
    AnnouncementCreate,
    AnnouncementOut,
    AnnouncementUpdate,
    CommentCreate,
    CommentOut,
    MessageOut,
    ResidentOut,
)
from ..services.residents import resident_out_map

router = APIRouter(prefix="/api/announcements", tags=["board"])


def _load_announcement(announcement_id: int, db: Session) -> Announcement | None:
    return db.scalar(
        select(Announcement)
        .options(
            joinedload(Announcement.creator),
            joinedload(Announcement.reads),
            joinedload(Announcement.comments),
        )
        .execution_options(populate_existing=True)
        .where(Announcement.id == announcement_id)
    )


def _require_announcement(announcement_id: int, db: Session) -> Announcement:
    announcement = _load_announcement(announcement_id, db)
    if announcement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anuncio no encontrado",
        )
    return announcement


def _comment_out(comment: AnnouncementComment, residents: dict[int, ResidentOut]) -> CommentOut:
    return CommentOut.model_validate(comment).model_copy(
        update={"author": residents.get(comment.resident_id)}
    )


def _as_out(
    announcement: Announcement,
    residents: dict[int, ResidentOut],
) -> AnnouncementOut:
    return AnnouncementOut.model_validate(announcement).model_copy(
        update={
            "creator": residents[announcement.created_by],
            "read_by": [read.resident_id for read in announcement.reads],
            "comments": [_comment_out(comment, residents) for comment in announcement.comments],
        }
    )


@router.get("", response_model=list[AnnouncementOut])
def list_announcements(
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    announcements = (
        db.scalars(
            select(Announcement)
            .options(
                joinedload(Announcement.creator),
                joinedload(Announcement.reads),
                joinedload(Announcement.comments),
            )
            .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
        )
        .unique()
        .all()
    )
    residents = resident_out_map(db)
    return [_as_out(announcement, residents) for announcement in announcements]


@router.post("", response_model=AnnouncementOut, status_code=status.HTTP_201_CREATED)
def create_announcement(
    payload: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    values = payload.model_dump()
    values["is_pinned"] = values["is_pinned"] if current_user.role == "committee" else False
    announcement = Announcement(**values, created_by=current_user.id)
    db.add(announcement)
    db.commit()
    return _as_out(_require_announcement(announcement.id, db), resident_out_map(db))


@router.patch("/{announcement_id}", response_model=AnnouncementOut)
def update_announcement(
    announcement_id: int,
    payload: AnnouncementUpdate,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(committee_only),
):
    announcement = _require_announcement(announcement_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(announcement, field, value)
    announcement.updated_at = datetime.now(timezone.utc)
    db.commit()
    return _as_out(_require_announcement(announcement_id, db), resident_out_map(db))


@router.delete("/{announcement_id}", response_model=MessageOut)
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(committee_only),
):
    announcement = _require_announcement(announcement_id, db)
    db.delete(announcement)
    db.commit()
    return MessageOut(message="Anuncio eliminado")


@router.post("/{announcement_id}/read", response_model=AnnouncementOut)
def mark_announcement_read(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    announcement = _require_announcement(announcement_id, db)
    existing = db.scalar(
        select(AnnouncementRead).where(
            AnnouncementRead.announcement_id == announcement.id,
            AnnouncementRead.resident_id == current_user.id,
        )
    )
    if existing is None:
        db.add(AnnouncementRead(announcement_id=announcement.id, resident_id=current_user.id))
        db.commit()
    return _as_out(_require_announcement(announcement_id, db), resident_out_map(db))


@router.delete("/{announcement_id}/read", response_model=AnnouncementOut)
def unmark_announcement_read(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    announcement = _require_announcement(announcement_id, db)
    existing = db.scalar(
        select(AnnouncementRead).where(
            AnnouncementRead.announcement_id == announcement.id,
            AnnouncementRead.resident_id == current_user.id,
        )
    )
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lectura no encontrada",
        )
    db.delete(existing)
    db.commit()
    return _as_out(_require_announcement(announcement_id, db), resident_out_map(db))


@router.post("/{announcement_id}/comments", response_model=CommentOut)
def create_comment(
    announcement_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    announcement = _require_announcement(announcement_id, db)
    comment = AnnouncementComment(
        announcement_id=announcement.id,
        resident_id=current_user.id,
        body=payload.body.strip(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _comment_out(comment, resident_out_map(db))


@router.delete("/{announcement_id}/comments/{comment_id}", response_model=MessageOut)
def delete_comment(
    announcement_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: Resident = Depends(get_current_user),
):
    _require_announcement(announcement_id, db)
    comment = db.get(AnnouncementComment, comment_id)
    if comment is None or comment.announcement_id != announcement_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comentario no encontrado",
        )
    if current_user.role != "committee" and comment.resident_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar este comentario",
        )
    db.delete(comment)
    db.commit()
    return MessageOut(message="Comentario eliminado")
