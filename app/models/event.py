#from email.policy import default
from typing import Optional, List, Any
from typing import Optional, TYPE_CHECKING
from sqlmodel import JSON, Column, Field, Relationship, SQLModel
from sqlalchemy import JSON
import uuid
import datetime

if TYPE_CHECKING:
    from models.event import Event
    from models.mltask import MLTask

class Event(SQLModel, table=True):
    """Модель данных для записи операций пользователей и событий в приложении"""
    __tablename__ = 'events'

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: Optional[str] = Field(default=None)
    user_id: int = Field(foreign_key="user.user_id")
    operation: Optional[str] = Field(default=None)
    is_admin: bool = Field(default=False)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)


    class Config:
        arbitrary_types_allowed = True

    def __repr__(self):
        return (f"<Event(id={self.id}, user_id={self.user_id}, "
                f"operation={self.operation}, time={self.created_at}>")
