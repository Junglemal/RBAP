from sqlmodel import Field, Relationship, SQLModel
from typing import Optional, List
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.event import Event
    from models.mltask import MLTask

class User(SQLModel, table=True):
    """Модель данных для пользователей"""
    __tablename__ = 'user'

    user_id: int = Field(unique=True, primary_key=True)
    name: str
    bank_position: str
    bank_unit: str
    email: str
    password: str
    is_admin: bool = Field(default=False)

    ml_tasks: List["MLTask"] = Relationship(
        back_populates="creator",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    @property
    def __str__(self) -> str:
        return (f'user_id: {self.user_id},'
                f'name: {self.name},'
                f'bank_position: {self.bank_position},'
                f'bank_unit: {self.bank_unit},'
                f'email: {self.email},'
                f'admin: {self.is_admin}'
                )
