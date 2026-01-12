from fastapi import APIRouter, Body, HTTPException, status, Depends, Query
from database.database import get_session
from models.event import Event
from models.user import User
from typing import Optional, List, Any
from sqlmodel import Session, select
from services.crud import event_crud as EventService
from services.crud.event_crud import new_event, get_all_events, get_event_by_id, get_user_events_by_id


def get_current_user(email: str, session=Depends(get_session)) -> User:
    from services.crud import user_crud as UserService
    user = UserService.get_user_by_email(email, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found.'
        )
    return user

event_route = APIRouter()
events = []

@event_route.get('/events')
async def get_events(
        email: str,
        target_email: Optional[str] = Query(None),
        all_users: Optional[bool] = Query(False),
        session=Depends(get_session)
) -> dict:
    """получение списка событий"""
    current_user = get_current_user(email, session)

    # Для админа: расширенные опции
    if current_user.is_admin:
        if all_users:
            # Посмотреть все события всех пользователей
            events = get_all_events(session)
            return {
                'is_admin': True,
                'view_mode': 'all_users',
                'events': events
            }
        elif target_email:
            # Посмотреть события конкретного пользователя
            target_user = get_current_user(target_email, session)
            events = get_user_events_by_id(target_user.user_id, session)
            return {
                'is_admin': True,
                'view_mode': 'specific_user',
                'target_user_id': target_user.user_id,
                'target_email': target_user.email,
                'events': events
            }

    # Для обычных пользователей или админов без специальных параметров - просмотр своих событий и операций
    events = get_user_events_by_id(current_user.user_id, session)
    if not events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No events found for user.'
        )
    return {
        'user_id': current_user.user_id,
        'email': current_user.email,
        'events': events
    }

@event_route.get('/events/{event_id}')
async def get_event_by_id_endpoint(
        event_id: str,
        email: str,
        session=Depends(get_session)
) -> dict:
    """получение события по id события"""
    current_user = get_current_user(email, session)
    events = get_event_by_id(event_id, session)

    if not events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No events found with ID: {event_id}'
        )

    # Проверяем доступ: админы могут видеть любые события, пользователи - только свои
    if not current_user.is_admin:
        user_events = [event for event in events if event.user_id == current_user.user_id]
        if not user_events:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Access denied to this event'
            )
        events = user_events

    return {
        'event_id': event_id,
        'events': events
    }
