import logging
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import Session, select
from database.database import get_session
from pydantic import BaseModel
from services.rm.rm import rabbit_client
from services.logging.logging import get_logger
from services.crud.mltask import MLTaskService
from models.mltask import MLTask, TaskStatus, MLTaskCreate, OperationType
from models.llm_prompts_model import llm_prompt_v1 # изменить импорт, при необходимости
from models.raw_parser_reviews import MortgageReview


logging.getLogger('pika').setLevel(logging.INFO)

logger = get_logger(logger_name=__name__)

ml_route = APIRouter()

class SendTaskResponse(BaseModel):
    message: str
    task_id: int
    operation_type: str
    review_id: Optional[int] = None
    bank_id: Optional[int] = None
    bank_name: Optional[str] = None
    user_city: Optional[str] = None

def get_mltask_service(session: Session = Depends(get_session)) -> MLTaskService:
    return MLTaskService(session)

@ml_route.post(
    "/send_task",
    response_model=SendTaskResponse,
    summary="endpoint для запроса обработки одного отзыва",
    description="Send single request to LLM"
)
async def send_task(
        message: str,
        user_id: int,
        review_id: Optional[int] = None,
        user_city: Optional[str] = None,
        bank_id: Optional[int] = None,
        bank_name: Optional[str] = None,
        mltask_service: MLTaskService = Depends(get_mltask_service)
) -> SendTaskResponse:
    """
    Endpoint для штучных запросов к LLM. Логика использования промпта из модели сохраняется.
    """
    created_task = None
    try:
        full_prompt = f"{llm_prompt_v1}\n\n{message}"

        mltask = MLTaskCreate(
            question=full_prompt,
            user_id=user_id,
            review_id=review_id,
            status=TaskStatus.NEW,
            operation_type=OperationType.SINGLE,
            user_city=user_city,
            bank_id=bank_id,
            bank_name=bank_name
        )

        created_task = mltask_service.create(mltask)
        logger.info(f"Task created: {created_task.id}, operation_type: {created_task.operation_type}")

        logger.info(f"Sending task to RabbitMQ: {created_task.id}")
        rabbit_client.send_task(created_task)
        mltask_service.set_status(created_task.id, TaskStatus.QUEUED)

        return SendTaskResponse(
            message="Task sent successfully!",
            task_id=created_task.id,
            operation_type=created_task.operation_type.value,
            review_id=created_task.review_id,
            bank_id=created_task.bank_id,
            bank_name=created_task.bank_name,
            user_city=created_task.user_city
        )
    except Exception as e:
        if created_task:
            mltask_service.set_status(created_task.id, TaskStatus.FAILED)
        logger.error(f"Unexpected error in sending task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@ml_route.post(
    "/send_task_batch",
    summary="Отправка батча отзывов из БД для обработки LLM",
    description="Process multiple reviews from database"
)
async def send_task_batch(
        user_id: int = Query(..., description="ID пользователя"),
        bank_id: Optional[int] = Query(None, description="ID банка для фильтрации"),
        limit: int = Query(10, ge=1, le=100, description="Количество отзывов для обработки (макс 100)"),
        date_from: Optional[datetime] = Query(None, description="Дата начала периода (по created_at_api)"),
        date_to: Optional[datetime] = Query(None, description="Дата окончания периода (по created_at_api)"),
        mltask_service: MLTaskService = Depends(get_mltask_service),
        session: Session = Depends(get_session)
):
    """
    Пакетная обработка отзывов из таблицы raw_parser_reviews
    """
    try:
        # Получаем отзывы, которые еще не обрабатывались
        query = select(MortgageReview).where(
            MortgageReview.text_api.is_not(None),
            MortgageReview.text_api != "",
            MortgageReview.text_api != "null"
        )

        # Фильтрация
        if bank_id:
            query = query.where(MortgageReview.bank_id == bank_id)
        if date_from:
            query = query.where(MortgageReview.created_at_api >= date_from)
        if date_to:
            query = query.where(MortgageReview.created_at_api <= date_to)

        # Исключаем уже обработанные отзывы (по review_id)
        subquery = select(MLTask.review_id).where(
            MLTask.review_id.is_not(None),
            MLTask.operation_type == OperationType.BATCH
        )
        query = query.where(MortgageReview.id.not_in(subquery))

        # Сортируем по дате создания отзыва (сначала новые)
        query = query.order_by(MortgageReview.created_at_api.desc())

        # Применяем лимит
        reviews = session.exec(query.limit(limit)).all()

        if not reviews:
            return {
                "message": "Нет отзывов для обработки по заданным критериям",
                "processed_count": 0,
                "tasks": []
            }

        # Формирование задачи на каждый отзыв
        created_tasks = []
        for review in reviews:
            # Формируем полный промпт с текстом отзыва
            full_prompt = f"{llm_prompt_v1}\n\n{review.text_api}"

            mltask = MLTaskCreate(
                question=full_prompt,
                user_id=user_id,
                review_id=review.id,
                status=TaskStatus.NEW,
                operation_type=OperationType.BATCH,
                user_city=review.user_city,
                bank_id=review.bank_id,
                bank_name=review.bank_name,
                created_at_api=review.created_at_api
            )

            # Создаем задачу
            created_task = mltask_service.create(mltask)

            # Отправляем в RabbitMQ
            rabbit_client.send_task(created_task)
            mltask_service.set_status(created_task.id, TaskStatus.QUEUED)

            # Сохраняем информацию для ответа
            created_tasks.append({
                "task_id": created_task.id,
                "review_id": review.id,
                "bank_id": review.bank_id,
                "bank_name": review.bank_name,
                "user_city": review.user_city,
                "text_preview": review.text_api[:100] + "..." if len(review.text_api) > 100 else review.text_api,
                "created_at_api": review.created_at_api.isoformat() if review.created_at_api else None
            })

        logger.info(f"Создано {len(created_tasks)} batch-задач для обработки отзывов")

        # Формируем статистику
        bank_ids = {task["bank_id"] for task in created_tasks}
        bank_names = {task["bank_name"] for task in created_tasks}

        return {
            "message": f"Успешно создано {len(created_tasks)} задач для обработки отзывов",
            "processed_count": len(created_tasks),
            "filters_applied": {
                "bank_id": bank_id,
                "limit": limit,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None
            },
            "statistics": {
                "unique_banks_count": len(bank_ids),
                "unique_bank_names": list(bank_names),
                "oldest_review": min(task["created_at_api"] for task in created_tasks if
                                     task["created_at_api"]) if created_tasks else None,
                "newest_review": max(task["created_at_api"] for task in created_tasks if
                                     task["created_at_api"]) if created_tasks else None
            },
            "tasks": created_tasks
        }

    except Exception as e:
        logger.error(f"Ошибка при обработке отзывов: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@ml_route.post("/send_task_result", response_model=Dict[str, str])
def send_task_result(
        task_id: int,
        result: str,
        mltask_service: MLTaskService = Depends(get_mltask_service)
) -> Dict[str, str]:
    """
    Endpoint for sending ML task using Result.
    """
    try:
        mltask_service.set_result(task_id, result)
        logger.info(f"Task result has been set: {result}")
        return {"message": "Task result sent successfully!"}
    except Exception as e:
        logger.error(f"Unexpected error in sending task result: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@ml_route.get("/tasks", response_model=List[MLTask])
async def get_all_tasks(
        mltask_service: MLTaskService = Depends(get_mltask_service)
):
    """Выгрузка всех сформированных задач"""
    return mltask_service.get_all()


@ml_route.get("/tasks/{task_id}", response_model=MLTask)
async def get_task(
        task_id: int,
        mltask_service: MLTaskService = Depends(get_mltask_service)
):
    """Получить задачу по ID."""
    task = mltask_service.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@ml_route.get("/batch_stats")
async def get_batch_stats(
        bank_id: Optional[int] = Query(None, description="ID банка для фильтрации"),
        date_from: Optional[datetime] = Query(None, description="Минимальная дата отзыва"),
        date_to: Optional[datetime] = Query(None, description="Максимальная дата отзыва"),
        session: Session = Depends(get_session)
):
    """
    Получить статистику по отзывам для batch-обработки
    """
    try:
        # Всего отзывов
        total_query = select(MortgageReview).where(
            MortgageReview.text_api.is_not(None),
            MortgageReview.text_api != ""
        )

        # Обработанные отзывы
        processed_subquery = select(MLTask.review_id).where(
            MLTask.review_id.is_not(None),
            MLTask.operation_type == OperationType.BATCH
        )

        # Необработанные отзывы
        pending_query = select(MortgageReview).where(
            MortgageReview.text_api.is_not(None),
            MortgageReview.text_api != "",
            MortgageReview.id.not_in(processed_subquery)
        )

        # Применяем фильтры
        if bank_id:
            total_query = total_query.where(MortgageReview.bank_id == bank_id)
            pending_query = pending_query.where(MortgageReview.bank_id == bank_id)

        if date_from:
            total_query = total_query.where(MortgageReview.created_at_api >= date_from)
            pending_query = pending_query.where(MortgageReview.created_at_api >= date_from)

        if date_to:
            total_query = total_query.where(MortgageReview.created_at_api <= date_to)
            pending_query = pending_query.where(MortgageReview.created_at_api <= date_to)

        # Подключаемся к БД, выполняем сформированные запросы
        total_reviews = session.exec(total_query).all()
        pending_reviews = session.exec(pending_query).all()

        # Группировка по банкам
        banks_stats = {}
        for review in total_reviews:
            bank_key = f"{review.bank_id}_{review.bank_name}"
            if bank_key not in banks_stats:
                banks_stats[bank_key] = {
                    "bank_id": review.bank_id,
                    "bank_name": review.bank_name,
                    "total_reviews": 0,
                    "pending_reviews": 0
                }
            banks_stats[bank_key]["total_reviews"] += 1

        for review in pending_reviews:
            bank_key = f"{review.bank_id}_{review.bank_name}"
            if bank_key in banks_stats:
                banks_stats[bank_key]["pending_reviews"] += 1

        return {
            "statistics": {
                "total_reviews": len(total_reviews),
                "processed_reviews": len(total_reviews) - len(pending_reviews),
                "pending_reviews": len(pending_reviews),
                "processing_percentage": round(((len(total_reviews) - len(pending_reviews)) / len(total_reviews) * 100),
                                               2) if total_reviews else 0
            },
            "banks": list(banks_stats.values())
        }

    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
