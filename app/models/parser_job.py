from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class ParserJob(SQLModel, table=True):
    """Модель для обновления статуса работы парсера"""
    __tablename__ = "parser_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)

    status: str  # running | finished | failed

    current_page: Optional[int] = None
    total_pages: Optional[int] = None
    processed_reviews: int = 0

    message: Optional[str] = None

    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
