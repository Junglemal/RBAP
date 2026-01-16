import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from database.database import get_session
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Body
from sqlmodel import Session, select, func, desc
from parser.parser import full_parse_cycle
from models.raw_parser_reviews import MortgageReview
from models.parser_run import ParserRunRequest
from models.parser_job import ParserJob


logger = logging.getLogger(__name__)

parser_route = APIRouter()

# -------- Вспомогательные функции

def review_to_dict(review: MortgageReview) -> Dict[str, Any]:
    """Преобразование отзыва в словарь"""
    return {
        "id": review.id,
        "title": review.title,
        "user_name_api": review.user_name_api,
        "user_name_page": review.user_name_page,
        "user_city": review.user_city,
        "grade_api": review.grade_api,
        "grade_page": review.grade_page,
        "text_api": review.text_api,
        "full_text": review.full_text,
        "created_at_api": review.created_at_api.isoformat() if review.created_at_api else None,
        "created_at_page": review.created_at_page.isoformat() if review.created_at_page else None,
        "comment_count": review.comment_count,
        "is_countable": review.is_countable,
        "status": review.status,
        "bank_id": review.bank_id,
        "bank_name": review.bank_name,
        "bank_region": review.bank_region,
        "bank_answer_api": review.bank_answer_api,
        "bank_answer_detailed": review.bank_answer_detailed,
        "agent_id": review.agent_id,
        "criteria_scores": review.criteria_scores,
        "comments": review.comments,
        "link_list": review.link_list,
        "link_page": review.link_page,
        "page_number": review.page_number,
        "parsed_at": review.parsed_at.isoformat() if review.parsed_at else None,
        "error": review.error,
    }


def job_to_dict(job: ParserJob) -> Dict[str, Any]:
    """Преобразование таски парсера в словарь"""
    return {
        "id": job.id,
        "status": job.status,
        "current_page": job.current_page,
        "total_pages": job.total_pages,
        "processed_reviews": job.processed_reviews,
        "message": job.message,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }


# -------- Логика управления парсером

@parser_route.post(
    "/run",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Запуск парсера с сохранением данных в БД и/или Excel",
    description="Run mortgage reviews parser"
)
async def run_parser(
        background_tasks: BackgroundTasks,
        data: ParserRunRequest = Body(...),
        session: Session = Depends(get_session),
) -> dict:
    try:
        # Формируем статус работы / задачи парсера в БД
        job = ParserJob(
            status="running",
            message="Parser job created"
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        # Запускаем парсер
        background_tasks.add_task(
            full_parse_cycle,
            start_page=data.start_page,
            end_page=data.end_page,
            filename=data.filename,
            delay=data.delay,
            resume=data.resume,
            save_to_db=data.save_to_db,
            job_id=job.id  # Передаем ID задачи
        )

        return {
            "message": "Parser started successfully",
            "job_id": job.id,
            "params": data.dict(),
            "save_to_db": data.save_to_db,
            "save_to_excel": data.filename is not None
        }

    except Exception as e:
        logger.error(f"Error starting parser: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start parser: {str(e)}"
        )


@parser_route.post(
    "/run/test",
    status_code=status.HTTP_200_OK,
    summary="Тести парсера / выгрузка единичной страницы",
    description="Test parser with one specific page"
)
async def test_parser(
        background_tasks: BackgroundTasks,
        page: int = 1,
        save_to_db: bool = True,
        session: Session = Depends(get_session),
) -> dict:
    try:
        job = ParserJob(
            status="running",
            message=f"Test parser for page {page}"
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        background_tasks.add_task(
            full_parse_cycle,
            start_page=page,
            end_page=page,
            filename=f"test_page_{page}.xlsx",
            delay=1,
            resume=False,
            save_to_db=save_to_db,
            job_id=job.id
        )

        return {
            "message": f"Test parser started for page {page}",
            "job_id": job.id,
            "save_to_db": save_to_db
        }

    except Exception as e:
        logger.error(f"Error starting test parser: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start test parser: {str(e)}"
        )

# -------- Логика по статусам / выгрузка всех задач парсера

@parser_route.get(
    "/jobs",
    summary="Get all parser jobs",
)
async def get_all_jobs(
        limit: int = 100,
        offset: int = 0,
        session: Session = Depends(get_session)
) -> List[Dict[str, Any]]:
    """Получить все задачи парсинга"""
    try:
        statement = select(ParserJob).order_by(desc(ParserJob.started_at)).offset(offset).limit(limit)
        results = session.exec(statement).all()

        return [job_to_dict(job) for job in results]
    except Exception as e:
        logger.error(f"Error getting jobs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get jobs: {str(e)}"
        )

@parser_route.get(
    "/jobs/{job_id}",
    summary="Get parser job by ID",
)
async def get_job_by_id(
        job_id: int,
        session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Получить задачу по ID"""
    try:
        job = session.get(ParserJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return job_to_dict(job)
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job: {str(e)}"
        )

@parser_route.get(
    "/jobs/{job_id}/reviews",
    summary="Get reviews from specific job",
)
async def get_job_reviews(
        job_id: int,
        limit: int = 100,
        offset: int = 0,
        session: Session = Depends(get_session)
) -> List[Dict[str, Any]]:
    """Получить отзывы по job_id)"""
    try:
        # Проверяем существование задачи
        job = session.get(ParserJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        statement = select(MortgageReview).order_by(desc(MortgageReview.parsed_at)).offset(offset).limit(limit)
        results = session.exec(statement).all()

        return [review_to_dict(review) for review in results]
    except Exception as e:
        logger.error(f"Error getting job reviews: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job reviews: {str(e)}"
        )

# -------- Логика выгрузки отзывов

@parser_route.get(
    "/reviews",
    summary="Get all reviews"
)
async def get_all_reviews(
        limit: int = 100,
        offset: int = 0,
        session: Session = Depends(get_session)
) -> List[Dict[str, Any]]:
    """Получить все отзывы"""
    try:
        statement = select(MortgageReview).order_by(desc(MortgageReview.parsed_at)).offset(offset).limit(limit)
        results = session.exec(statement).all()

        return [review_to_dict(review) for review in results]
    except Exception as e:
        logger.error(f"Error getting reviews: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reviews: {str(e)}"
        )

@parser_route.get(
    "/reviews/search",
    summary="Search reviews"
)
async def search_reviews(
        bank_name: Optional[str] = None,
        status: Optional[str] = None,
        min_grade: Optional[int] = None,
        max_grade: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
        session: Session = Depends(get_session)
) -> List[Dict[str, Any]]:
    """Поиск отзывов"""
    try:
        statement = select(MortgageReview)

        if bank_name:
            statement = statement.where(MortgageReview.bank_name.contains(bank_name))
        if status:
            statement = statement.where(MortgageReview.status == status)
        if min_grade is not None:
            statement = statement.where(MortgageReview.grade_api >= min_grade)
        if max_grade is not None:
            statement = statement.where(MortgageReview.grade_api <= max_grade)

        statement = statement.order_by(desc(MortgageReview.parsed_at)).offset(offset).limit(limit)
        results = session.exec(statement).all()

        return [review_to_dict(review) for review in results]
    except Exception as e:
        logger.error(f"Error searching reviews: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search reviews: {str(e)}"
        )

@parser_route.get(
    "/reviews/bank/{bank_id}",
    summary="Get parsed reviews by bank",
)
async def get_reviews_by_bank(
        bank_id: int,
        limit: int = 100,
        offset: int = 0,
        session: Session = Depends(get_session)
) -> List[Dict[str, Any]]:
    """Получить отзывы по банку"""
    try:
        statement = (
            select(MortgageReview)
            .where(MortgageReview.bank_id == bank_id)
            .order_by(desc(MortgageReview.parsed_at))
            .offset(offset)
            .limit(limit)
        )
        results = session.exec(statement).all()

        return [review_to_dict(review) for review in results]
    except Exception as e:
        logger.error(f"Error getting reviews for bank {bank_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bank reviews: {str(e)}"
        )

# -------- Логика выгрузки / удаления штучных отзывов
# + удаление отзывов по статусу
# (необходимо при отчистке отзывов при переходе их с проверки к новому статусу на сайте)

@parser_route.get(
    "/reviews/{review_id}",
    summary="Get parsed review by ID",
)
async def get_review_by_id(
        review_id: int,
        session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Получить отзыв по ID"""
    try:
        review = session.get(MortgageReview, review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        return review_to_dict(review)
    except Exception as e:
        logger.error(f"Error getting review {review_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get review: {str(e)}"
        )

@parser_route.delete(
    "/reviews/{review_id}",
    summary="Delete parsed review by ID",
)
async def delete_review_by_id(
        review_id: int,
        session: Session = Depends(get_session)
) -> dict:
    """Удалить отзыв по ID"""
    try:
        review = session.get(MortgageReview, review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        session.delete(review)
        session.commit()
        return {"message": "Review deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting review {review_id}: {str(e)}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete review: {str(e)}"
        )

@parser_route.delete(
    "/reviews/status/{status_name}",
    summary="Delete parsed reviews by status",
)
async def delete_reviews_by_status(
        status_name: str,
        session: Session = Depends(get_session)
) -> dict:
    """Удалить отзывы по статусу"""
    try:
        statement = select(MortgageReview).where(MortgageReview.status == status_name)
        reviews = session.exec(statement).all()

        deleted_count = 0
        for review in reviews:
            session.delete(review)
            deleted_count += 1

        session.commit()
        return {
            "status": status_name,
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Error deleting reviews by status {status_name}: {str(e)}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete reviews by status: {str(e)}"
        )


# -------- Формирование статистики по работе парсера и данным

@parser_route.get(
    "/stats/summary",
    summary="Get parsing statistics"
)
async def get_parser_stats(
        session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Получить статистику парсинга"""
    try:
        # Общее количество отзывов
        statement = select(func.count(MortgageReview.id))
        total_reviews = session.exec(statement).one()

        # Отзывы по статусам
        status_statement = select(
            MortgageReview.status,
            func.count(MortgageReview.id)
        ).group_by(MortgageReview.status)

        status_results = session.exec(status_statement).all()
        status_stats = {status: count for status, count in status_results}

        # Последний запуск парсера
        job_statement = select(ParserJob).order_by(desc(ParserJob.started_at)).limit(1)
        last_job = session.exec(job_statement).first()

        return {
            "total_reviews": total_reviews,
            "status_distribution": status_stats,
            "last_job": {
                "id": last_job.id if last_job else None,
                "status": last_job.status if last_job else None,
                "started_at": last_job.started_at.isoformat() if last_job and last_job.started_at else None,
                "finished_at": last_job.finished_at.isoformat() if last_job and last_job.finished_at else None
            }
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get parser statistics: {str(e)}"
        )

@parser_route.get(
    "/stats/banks",
    summary="Get bank statistics"
)
async def get_bank_stats(
        session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Получить статистику по банкам"""
    try:
        # Получаем все отзывы с банками
        statement = select(MortgageReview).where(MortgageReview.bank_id.isnot(None))
        all_reviews = session.exec(statement).all()

        # Группируем по банкам
        bank_stats = {}
        for review in all_reviews:
            if review.bank_id:
                bank_id = str(review.bank_id)
                if bank_id not in bank_stats:
                    bank_stats[bank_id] = {
                        "bank_id": review.bank_id,
                        "bank_name": review.bank_name or "Неизвестно",
                        "total_reviews": 0,
                        "average_rating": 0,
                        "status_counts": {}
                    }

                bank_stats[bank_id]["total_reviews"] += 1

                if review.grade_api is not None:
                    current_total = bank_stats[bank_id]["total_reviews"]
                    current_avg = bank_stats[bank_id]["average_rating"]
                    bank_stats[bank_id]["average_rating"] = (
                            (current_avg * (current_total - 1) + review.grade_api) / current_total
                    )

                if review.status:
                    if review.status not in bank_stats[bank_id]["status_counts"]:
                        bank_stats[bank_id]["status_counts"][review.status] = 0
                    bank_stats[bank_id]["status_counts"][review.status] += 1

        return {
            "banks": list(bank_stats.values()),
            "total_banks": len(bank_stats)
        }
    except Exception as e:
        logger.error(f"Error getting bank stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bank statistics: {str(e)}"
        )

# -------- Функции проверки работоспособности парсера // Healthcheck

@parser_route.get(
    "/health",
    summary="Check parser health"
)
async def health_check(
        session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Healthcheck"""
    try:
        # Проверяем подключение к БД
        review_count = session.exec(select(func.count(MortgageReview.id))).one()
        job_count = session.exec(select(func.count(ParserJob.id))).one()

        return {
            "status": "healthy",
            "database": "connected",
            "reviews_count": review_count,
            "jobs_count": job_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# -------- Вспомогательная функция по обновлению статусов

@parser_route.put(
    "/jobs/{job_id}/update",
    summary="Update parser job status",
)
async def update_job_status(
        job_id: int,
        status: Optional[str] = None,
        current_page: Optional[int] = None,
        total_pages: Optional[int] = None,
        processed_reviews: Optional[int] = None,
        message: Optional[str] = None,
        session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """Обновить статус задачи парсинга"""
    try:
        job = session.get(ParserJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if status is not None:
            job.status = status
        if current_page is not None:
            job.current_page = current_page
        if total_pages is not None:
            job.total_pages = total_pages
        if processed_reviews is not None:
            job.processed_reviews = processed_reviews
        if message is not None:
            job.message = message

        # Если статус finished или failed, устанавливаем finished_at
        if status in ["finished", "failed"] and job.finished_at is None:
            job.finished_at = datetime.utcnow()

        session.add(job)
        session.commit()
        session.refresh(job)

        return job_to_dict(job)
    except Exception as e:
        logger.error(f"Error updating job {job_id}: {str(e)}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update job: {str(e)}"
        )
