from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum


if TYPE_CHECKING:
    from models.user import User


class TaskStatus(str, Enum):
    """Статусы выполнения ML задачи"""
    NEW = "new"  # Новая задача
    QUEUED = "queued"  # В очереди на выполнение
    PROCESSING = "processing"  # В процессе обработки
    COMPLETED = "completed"  # Выполнена
    FAILED = "failed"  # Ошибка выполнения

class OperationType(str, Enum):
    """Типы операций ML задачи"""
    SINGLE = "single_operation"  # Единичный запрос
    BATCH = "batch_operation"    # Пакетная обработка


class MLTaskBase(SQLModel):
    """
    Базовая модель ML задачи.

    Атрибуты:
        status (TaskStatus): Текущий статус задачи
        result (Optional[str]): Результат обработки ML моделью (ответ LLM по промпту)
        operation_type (OperationType): Тип операции
        review_id (Optional[int]): ID отзыва
        user_city (Optional[str]): Город пользователя
        bank_id (Optional[int]): ID банка
        bank_name (Optional[str]): Название банка
        created_at_api: Optional[datetime]: Дата отзыва
    """
    status: TaskStatus = Field(default=TaskStatus.NEW)
    result: Optional[str] = Field(default=None)
    question: Optional[str] = Field(default=None)
    operation_type: OperationType = Field(default=OperationType.SINGLE)
    review_id: Optional[int] = Field(default=None)
    user_city: Optional[str] = Field(default=None)
    bank_id: Optional[int] = Field(default=None)
    bank_name: Optional[str] = Field(default=None)
    created_at_api: Optional[datetime] = Field(default=None)

class MLTask(MLTaskBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.user_id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    creator: Optional["User"] = Relationship(
        back_populates="ml_tasks",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    def to_queue_message(self) -> dict:
        """Формирует сообщение для отправки в RabbitMQ"""
        return {
            "task_id": self.id,
            "question": self.question,
            "review_id": self.review_id,
            "operation_type": self.operation_type,
            "user_city": self.user_city,
            "bank_id": self.bank_id,
            "bank_name": self.bank_name
        }


class MLTaskCreate(MLTaskBase):
    """DTO для создания новой ML задачи"""
    question: str
    user_id: int
    status: TaskStatus
    operation_type: OperationType = Field(default=OperationType.SINGLE)
    review_id: Optional[int] = None
    user_city: Optional[str] = None
    bank_id: Optional[int] = None
    bank_name: Optional[str] = None


class MLTaskUpdate(MLTaskBase):
    """DTO для обновления существующей ML задачи"""
    status: Optional[TaskStatus] = None
    result: Optional[str] = None
