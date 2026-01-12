from sqlmodel import Field, SQLModel
from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSON


class MortgageReview(SQLModel, table=True):
    """Модель данных для необработанных данных парсера"""
    __tablename__ = 'raw_parser_reviews'

    id: int = Field(primary_key=True)

    title: Optional[str] = None

    user_name_api: Optional[str] = None
    user_name_page: Optional[str] = None
    user_city: Optional[str] = None

    grade_api: Optional[int] = None
    grade_page: Optional[int] = None

    text_api: Optional[str] = None
    full_text: Optional[str] = None

    created_at_api: Optional[datetime] = None
    created_at_page: Optional[datetime] = None

    comment_count: Optional[int] = None
    is_countable: Optional[bool] = None
    status: Optional[str] = None

    bank_id: int
    bank_name: str
    bank_region: Optional[str] = None

    bank_answer_api: Optional[str] = None
    bank_answer_detailed: Optional[str] = None

    agent_id: Optional[int] = None

    # 🔥 ВАЖНО: JSON-поля
    criteria_scores: Optional[Dict] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True)
    )

    comments: Optional[List] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True)
    )

    link_list: str
    link_page: str

    page_number: int
    parsed_at: datetime = Field(default_factory=datetime.utcnow)

    error: Optional[str] = None
