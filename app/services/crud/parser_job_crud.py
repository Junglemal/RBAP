from sqlmodel import Session, select, desc
from datetime import datetime
from models.parser_job import ParserJob
from typing import List, Optional

def create_job(session: Session) -> ParserJob:
    job = ParserJob(status="running")
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def update_job(
    job_id: int,
    session: Session,
    **kwargs
) -> None:
    job = session.get(ParserJob, job_id)
    if not job:
        return

    for key, value in kwargs.items():
        setattr(job, key, value)

    session.add(job)
    session.commit()


def finish_job(
    job_id: int,
    session: Session,
    status: str,
    message: str | None = None
) -> None:
    job = session.get(ParserJob, job_id)
    if not job:
        return

    job.status = status
    job.message = message
    job.finished_at = datetime.utcnow()

    session.add(job)
    session.commit()

def get_all_jobs(session: Session, limit: int = 100, offset: int = 0) -> List[ParserJob]:
    """Получить все задачи парсинга"""
    statement = select(ParserJob).order_by(desc(ParserJob.created_at)).offset(offset).limit(limit)
    results = session.exec(statement).all()
    return results

def get_last_job(session: Session) -> Optional[ParserJob]:
    """Получить последнюю задачу парсинга"""
    statement = select(ParserJob).order_by(desc(ParserJob.created_at)).limit(1)
    result = session.exec(statement).first()
    return result