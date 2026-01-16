from sqlmodel import Session, select, func
from typing import List, Optional, Dict
from models.raw_parser_reviews import MortgageReview


def get_all_reviews(session: Session) -> List[MortgageReview]:
    """Получить все отзывы"""
    query = select(MortgageReview)
    result = session.exec(query).all()

    return  result

def create_review(review: MortgageReview, session: Session) -> MortgageReview:
    """Загрузка одного отзыва"""
    review_to_add = MortgageReview(**review.model_dump())
    session.add(review_to_add)
    session.commit()
    session.refresh(review_to_add)

    return review_to_add

def bulk_create_reviews(reviews: List[MortgageReview], session: Session) -> int:
    """Батч загрузка отзывов"""
    objects = [
        MortgageReview(**review.model_dump())
        for review in reviews
    ]
    session.add_all(objects)
    session.commit()

    return len(objects)

def review_exists(review_id: int, session: Session) -> bool:
    """Проверка, существует ли отзыв в БД"""
    query = select(MortgageReview.id).where(MortgageReview.id == review_id)

    return session.exec(query).first() is not None

def upsert_review(review: MortgageReview, session: Session) -> MortgageReview:
    """Загрузка отзыва, если его нет в БД"""
    existing = session.get(MortgageReview, review.id)
    if existing:
        return existing
    session.add(review)
    session.commit()
    session.refresh(review)

    return review

def get_review_by_id(review_id: int, session: Session) -> Optional[MortgageReview]:
    """Получить отзыв по id"""
    return session.get(MortgageReview, review_id)

def get_reviews_by_bank(bank_id: int, session: Session, limit: int = 100, offset: int = 0) -> List[MortgageReview]:
    """Получить отзывы по банку"""
    query = (
        select(MortgageReview)
        .where(MortgageReview.bank_id == bank_id)
        .offset(offset)
        .limit(limit)
    )

    return session.exec(query).all()

def get_failed_reviews(session: Session) -> List[MortgageReview]:
    """Получить отзывы с ошибками парсинга"""
    query = select(MortgageReview).where(
        MortgageReview.error.is_not(None)
    )

    return session.exec(query).all()

def delete_review_by_id(review_id: int, session: Session) -> bool:
    """Удалить отзыв по id"""
    review = session.get(MortgageReview, review_id)
    if not review:
        return False

    session.delete(review)
    session.commit()

    return True

def delete_reviews_by_status(status: str, session: Session) -> int:
    """
    Удаление всех отзывов с указанным статусом.
    Использую для повторного парсинга,
    когда статусы отзывов обновляются на сайте.
    """
    query = select(MortgageReview).where(MortgageReview.status == status)
    reviews = session.exec(query).all()
    for review in reviews:
        session.delete(review)

    session.commit()

    return len(reviews)

def get_reviews_count(session: Session) -> int:
    """Получить общее количество отзывов"""
    statement = select(func.count(MortgageReview.id))
    result = session.exec(statement).one()
    return result

def get_reviews_by_status_count(session: Session) -> Dict[str, int]:
    """Получить количество отзывов по статусам"""
    statement = select(
        MortgageReview.status,
        func.count(MortgageReview.id)
    ).group_by(MortgageReview.status)

    results = session.exec(statement).all()
    return {status: count for status, count in results}

def get_all_reviews(session: Session, limit: int = 100, offset: int = 0) -> List[MortgageReview]:
    """Получить все отзывы с пагинацией"""
    statement = select(MortgageReview).offset(offset).limit(limit)
    results = session.exec(statement).all()
    return results
