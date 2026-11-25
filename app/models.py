from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Resident(Base):
    __tablename__ = "torre_residents"
    __table_args__ = (
        Index("ix_torre_residents_dept_number", "dept_number"),
        Index("ix_torre_residents_role", "role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dept_number: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="resident")
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    emergency_name: Mapped[str | None] = mapped_column(String(60), nullable=True)
    emergency_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    avatar_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6366f1")
    avatar_icon: Mapped[str] = mapped_column(String(8), nullable=False, default="🏠")
    pin_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    created_announcements: Mapped[list["Announcement"]] = relationship(
        back_populates="creator",
        foreign_keys="Announcement.created_by",
    )
    announcement_reads: Mapped[list["AnnouncementRead"]] = relationship(
        back_populates="reader",
        foreign_keys="AnnouncementRead.resident_id",
    )
    comments: Mapped[list["AnnouncementComment"]] = relationship(
        back_populates="author",
        foreign_keys="AnnouncementComment.resident_id",
    )
    assigned_chores: Mapped[list["Chore"]] = relationship(
        back_populates="assignee",
        foreign_keys="Chore.assigned_to",
    )
    created_chores: Mapped[list["Chore"]] = relationship(
        back_populates="creator",
        foreign_keys="Chore.created_by",
    )
    completed_chores: Mapped[list["Chore"]] = relationship(
        back_populates="completer",
        foreign_keys="Chore.completed_by",
    )
    expenses: Mapped[list["Expense"]] = relationship(
        back_populates="creator",
        foreign_keys="Expense.created_by",
    )
    contributions: Mapped[list["Contribution"]] = relationship(
        back_populates="resident",
        foreign_keys="Contribution.resident_id",
    )
    reviewed_contributions: Mapped[list["Contribution"]] = relationship(
        back_populates="approver",
        foreign_keys="Contribution.approved_by",
    )
    owned_spots: Mapped[list["ParkingSpot"]] = relationship(
        back_populates="owner",
        foreign_keys="ParkingSpot.owner_id",
    )
    borrowed_spots: Mapped[list["ParkingSpot"]] = relationship(
        back_populates="borrower",
        foreign_keys="ParkingSpot.borrower_id",
    )


class Announcement(Base):
    __tablename__ = "torre_announcements"
    __table_args__ = (
        Index("ix_torre_announcements_pinned", "is_pinned"),
        Index("ix_torre_announcements_created_at", "created_at"),
        Index("ix_torre_announcements_creator", "created_by"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False, default="Avisos Generales")
    is_pinned: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_by: Mapped[int] = mapped_column(
        ForeignKey("torre_residents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    creator: Mapped[Resident] = relationship(
        back_populates="created_announcements",
        foreign_keys=[created_by],
    )
    reads: Mapped[list["AnnouncementRead"]] = relationship(
        back_populates="announcement",
        cascade="all, delete-orphan",
    )
    comments: Mapped[list["AnnouncementComment"]] = relationship(
        back_populates="announcement",
        cascade="all, delete-orphan",
    )


class AnnouncementRead(Base):
    __tablename__ = "torre_announcement_reads"
    __table_args__ = (
        UniqueConstraint(
            "announcement_id",
            "resident_id",
            name="uq_torre_announcement_reads_announcement_resident",
        ),
        Index("ix_torre_announcement_reads_resident", "resident_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    announcement_id: Mapped[int] = mapped_column(
        ForeignKey("torre_announcements.id", ondelete="CASCADE"),
        nullable=False,
    )
    resident_id: Mapped[int] = mapped_column(
        ForeignKey("torre_residents.id", ondelete="CASCADE"),
        nullable=False,
    )
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    announcement: Mapped[Announcement] = relationship(back_populates="reads")
    reader: Mapped[Resident] = relationship(
        back_populates="announcement_reads",
        foreign_keys=[resident_id],
    )


class AnnouncementComment(Base):
    __tablename__ = "torre_announcement_comments"
    __table_args__ = (
        Index("ix_torre_announcement_comments_announcement", "announcement_id"),
        Index("ix_torre_announcement_comments_resident", "resident_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    announcement_id: Mapped[int] = mapped_column(
        ForeignKey("torre_announcements.id", ondelete="CASCADE"),
        nullable=False,
    )
    resident_id: Mapped[int] = mapped_column(
        ForeignKey("torre_residents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    announcement: Mapped[Announcement] = relationship(back_populates="comments")
    author: Mapped[Resident] = relationship(
        back_populates="comments",
        foreign_keys=[resident_id],
    )


class Chore(Base):
    __tablename__ = "torre_chores"
    __table_args__ = (
        Index("ix_torre_chores_completed", "is_completed"),
        Index("ix_torre_chores_due_date", "due_date"),
        Index("ix_torre_chores_assigned_to", "assigned_to"),
        Index("ix_torre_chores_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    area: Mapped[str] = mapped_column(String(24), nullable=False, default="Otro")
    frequency: Mapped[str] = mapped_column(String(16), nullable=False, default="Única")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    assigned_to: Mapped[int | None] = mapped_column(
        ForeignKey("torre_residents.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("torre_residents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    is_completed: Mapped[bool] = mapped_column(nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[int | None] = mapped_column(
        ForeignKey("torre_residents.id", ondelete="SET NULL"),
        nullable=True,
    )
    evidence_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_chore_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    assignee: Mapped[Resident | None] = relationship(
        back_populates="assigned_chores",
        foreign_keys=[assigned_to],
    )
    creator: Mapped[Resident] = relationship(
        back_populates="created_chores",
        foreign_keys=[created_by],
    )
    completer: Mapped[Resident | None] = relationship(
        back_populates="completed_chores",
        foreign_keys=[completed_by],
    )


class Expense(Base):
    __tablename__ = "torre_expenses"
    __table_args__ = (
        Index("ix_torre_expenses_spent_on", "spent_on"),
        Index("ix_torre_expenses_creator", "created_by"),
        Index("ix_torre_expenses_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False, default="Otro")
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    spent_on: Mapped[date] = mapped_column(Date, nullable=False)
    receipt_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(
        ForeignKey("torre_residents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    creator: Mapped[Resident] = relationship(
        back_populates="expenses",
        foreign_keys=[created_by],
    )


class Contribution(Base):
    __tablename__ = "torre_contributions"
    __table_args__ = (
        Index("ix_torre_contributions_resident", "resident_id"),
        Index("ix_torre_contributions_period", "period"),
        Index("ix_torre_contributions_status", "status"),
        Index("ix_torre_contributions_approved_by", "approved_by"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resident_id: Mapped[int] = mapped_column(
        ForeignKey("torre_residents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    proof_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="Pendiente")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey("torre_residents.id", ondelete="RESTRICT"),
        nullable=True,
    )

    resident: Mapped[Resident] = relationship(
        back_populates="contributions",
        foreign_keys=[resident_id],
    )
    approver: Mapped[Resident | None] = relationship(
        back_populates="reviewed_contributions",
        foreign_keys=[approved_by],
    )


class ParkingSpot(Base):
    __tablename__ = "torre_parking_spots"
    __table_args__ = (
        Index("ix_torre_parking_spots_status", "status"),
        Index("ix_torre_parking_spots_owner", "owner_id"),
        Index("ix_torre_parking_spots_borrower", "borrower_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    spot_type: Mapped[str] = mapped_column(String(16), nullable=False, default="Cubo")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="Disponible")
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("torre_residents.id", ondelete="RESTRICT"),
        nullable=True,
    )
    borrower_id: Mapped[int | None] = mapped_column(
        ForeignKey("torre_residents.id", ondelete="SET NULL"),
        nullable=True,
    )
    loan_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped[Resident | None] = relationship(
        back_populates="owned_spots",
        foreign_keys=[owner_id],
    )
    borrower: Mapped[Resident | None] = relationship(
        back_populates="borrowed_spots",
        foreign_keys=[borrower_id],
    )
