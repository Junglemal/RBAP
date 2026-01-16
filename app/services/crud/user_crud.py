from sqlmodel import Session, select
from typing import List, Optional
from models.user import User


def create_user(user: User, session: Session) -> User:
    """Создание пользователя"""
    user_to_add = User(
        user_id = user.user_id,
        name = user.name,
        bank_position = user.bank_position,
        bank_unit = user.bank_unit,
        email = user.email,
        password = user.password,
        is_admin = user.is_admin
    )
    session.add(user_to_add)
    session.commit()
    session.refresh(user_to_add)

    return user_to_add

def delete_user_by_id(user_id: int, session: Session) -> bool:
    """Удаление пользователя по id"""
    user_to_delete = get_user_by_id(user_id, session)
    if user_to_delete:
        session.delete(user_to_delete)
        session.commit()
        return True
    else:
        return False

def get_all_users(session: Session) -> List[User]:
    """Получить список всех пользователей"""
    query = select(User)
    result = session.exec(query).all()
    return  result

def get_user_by_id(user_id: int, session: Session) -> Optional[User]:
    """Получить пользователя по id"""
    query = select(User).where(User.user_id == user_id)
    result = session.exec(query).first()
    return result

def get_user_by_email(user_email: str, session: Session) -> Optional[User]:
    """Получить пользователя по email"""
    query = select(User).where(User.email == user_email)
    result = session.exec(query).first()
    return result
