from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["committee", "resident"]
AnnouncementCategory = Literal["Urgente", "Mantenimiento", "Avisos Generales", "Acuerdos"]
ChoreArea = Literal[
    "Escaleras",
    "Pasillos",
    "Área de basura",
    "Tinacos",
    "Cisterna",
    "Jardín",
    "Otro",
]
Frequency = Literal["Semanal", "Mensual", "Única"]
ChoreFilter = Literal["all", "mine", "pending", "completed"]
ExpenseCategory = Literal["Limpieza", "Reparación", "Luz", "Agua", "Seguridad", "Otro"]
ContributionKind = Literal["Cuota mensual", "Cooperación extraordinaria"]
ContributionStatus = Literal["Pendiente", "Aprobada", "Rechazada"]
ParkingSpotType = Literal["Cubo", "Descubierto"]
ParkingStatus = Literal["Disponible", "Solicitado", "Prestado"]


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dept_number: int
    name: str
    role: Role
    avatar_color: str
    avatar_icon: str


class ResidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dept_number: int
    name: str
    role: Role
    phone: str | None = None
    emergency_name: str | None = None
    emergency_phone: str | None = None
    avatar_color: str
    avatar_icon: str
    account_status: str = "Con adeudo"
    amount_paid: float = 0.0
    created_at: datetime


class PINLogin(BaseModel):
    dept_number: int
    pin: str = Field(min_length=1, max_length=72)


class ResidentUpdate(BaseModel):
    phone: str | None = None
    emergency_name: str | None = None
    emergency_phone: str | None = None
    role: Role | None = None


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    announcement_id: int
    resident_id: int
    body: str
    created_at: datetime
    author: ResidentOut | None = None


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=140)
    body: str = Field(min_length=1, max_length=4000)
    category: AnnouncementCategory = "Avisos Generales"
    is_pinned: bool = False


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=140)
    body: str | None = Field(default=None, min_length=1, max_length=4000)
    category: AnnouncementCategory | None = None
    is_pinned: bool | None = None


class AnnouncementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str
    category: str
    is_pinned: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    creator: ResidentOut
    read_by: list[int] = []
    comments: list[CommentOut] = []


class ChoreCreate(BaseModel):
    title: str = Field(min_length=1, max_length=140)
    description: str | None = Field(default=None, max_length=2000)
    area: ChoreArea = "Otro"
    frequency: Frequency = "Única"
    due_date: date | None = None
    assigned_to: int | None = None


class ChoreUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=140)
    description: str | None = Field(default=None, max_length=2000)
    area: ChoreArea | None = None
    frequency: Frequency | None = None
    due_date: date | None = None
    assigned_to: int | None = None
    evidence_url: str | None = None


class ChoreComplete(BaseModel):
    evidence_url: str | None = None


class ChoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    area: str
    frequency: str
    due_date: date | None = None
    assigned_to: int | None = None
    created_by: int
    created_at: datetime
    is_completed: bool
    completed_at: datetime | None = None
    completed_by: int | None = None
    evidence_url: str | None = None
    next_chore_id: int | None = None
    assignee: ResidentOut | None = None
    creator: ResidentOut
    completer: ResidentOut | None = None


class ExpenseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=140)
    category: ExpenseCategory = "Otro"
    amount: float = Field(gt=0)
    spent_on: date
    receipt_url: str | None = None


class ExpenseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=140)
    category: ExpenseCategory | None = None
    amount: float | None = Field(default=None, gt=0)
    spent_on: date | None = None
    receipt_url: str | None = None


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    category: str
    amount: float
    spent_on: date
    receipt_url: str | None = None
    created_by: int
    created_at: datetime
    creator: ResidentOut


class ContributionCreate(BaseModel):
    resident_id: int | None = None
    kind: ContributionKind
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    amount: float = Field(gt=0)
    proof_url: str | None = None


class ContributionReview(BaseModel):
    action: Literal["approve", "reject"]


class ContributionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resident_id: int
    kind: str
    period: str
    amount: float
    proof_url: str | None = None
    status: str
    created_at: datetime
    approved_at: datetime | None = None
    resident: ResidentOut
    approver: ResidentOut | None = None


class FinanceSummaryOut(BaseModel):
    opening_balance: float
    cash_balance: float
    collected_this_month: float
    spent_this_month: float
    pending_reviews: int


class ParkingCreate(BaseModel):
    code: str = Field(min_length=1, max_length=24)
    location: str = Field(min_length=1, max_length=120)
    spot_type: ParkingSpotType = "Cubo"
    owner_id: int | None = None
    loan_until: date | None = None
    note: str | None = None


class ParkingUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=24)
    location: str | None = Field(default=None, min_length=1, max_length=120)
    spot_type: ParkingSpotType | None = None
    status: ParkingStatus | None = None
    owner_id: int | None = None
    borrower_id: int | None = None
    loan_until: date | None = None
    note: str | None = None


class ParkingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    location: str
    spot_type: str
    status: str
    owner_id: int | None = None
    borrower_id: int | None = None
    loan_until: date | None = None
    note: str | None = None
    owner: ResidentOut | None = None
    borrower: ResidentOut | None = None


class MessageOut(BaseModel):
    message: str
