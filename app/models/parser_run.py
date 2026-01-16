from pydantic import BaseModel
from typing import Optional


class ParserRunRequest(BaseModel):
    """Модель для конфигурации запуска парсера"""
    start_page: int = 1
    end_page: Optional[int] = None
    delay: int = 2
    resume: bool = True
    save_to_db: bool = True
    filename: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "start_page": 1,
                "end_page": 10,
                "delay": 2,
                "resume": True,
                "save_to_db": True,
                "filename": "mortgage_reviews.xlsx"
            }
        }
    }
