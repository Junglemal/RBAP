# В версии 1.0 все операции с моделью, crud и api по event отключены
# до перехода к промышленным тестам с бизнес-пользователями
from typing import List
from sqlmodel import Session, select
from models.event import Event
from models.user import User


def new_event(event: Event, session: Session) -> Event:
    """Создание нового события"""
    session.add(event)
    session.commit()
    session.refresh(event)
    return event

def get_all_events(session: Session) -> List[Event]:
    """Получить список всех событий и операций"""
    query = select(Event)
    result = session.exec(query).all()
    return result

def get_event_by_id(event_id: str, session: Session) -> List[Event]:
    """Получить событие по его id"""
    query = select(Event).where(Event.event_id == event_id)
    result = session.exec(query).all()
    return result

def get_user_events_by_id(user_id: int, session: Session):
    """Получение события по id пользователя"""
    query = select(Event).where(Event.user_id == user_id)
    result = session.exec(query).all()
    return result
