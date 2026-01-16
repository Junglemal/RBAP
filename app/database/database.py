from sqlmodel import SQLModel, Session, create_engine
from contextlib import contextmanager
from .config import get_settings
from auth.hash_password import HashPassword
from models.user import User
from models.event import Event
from models.mltask import MLTask
from models.raw_parser_reviews import MortgageReview
from services.crud.user_crud import get_user_by_id, get_user_by_email, get_all_users, create_user


def get_database_engine():
    """
    Create and configure the SQLAlchemy engine.
    Returns:
        Engine: Configured SQLAlchemy engine
    """
    settings = get_settings()
    engine = create_engine(
        url=settings.DATABASE_URL_psycopg,
        echo=settings.DEBUG,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600
    )
    return engine

engine = get_database_engine()

def get_session():
    with Session(engine) as session:
        yield session

def init_db(drop_all: bool = False) -> None:
    """
    Initialize database schema.
    Args:
        drop_all: If True, drops all tables before creation
    Raises:
        Exception: Any database-related exception
    """
    try:
        engine = get_database_engine()
        if drop_all:
            SQLModel.metadata.drop_all(engine)

        SQLModel.metadata.create_all(engine)

    # инициализация "демо" пользователей
        with Session(engine) as session:
        # создаём обычного пользователя подразделения продаж
            hash_password = HashPassword()

            sales_user = create_user(
                User(name="regular_sales_user",
                     bank_position="UD",
                     bank_unit="sales",
                     email="ud@gmail.com",
                     password=hash_password.create_hash("123456"),
                     is_admin=False),
                session,
            )

            stream_user = create_user(
                User(name="regular_stream_user",
                     bank_position="cluster_lead",
                     bank_unit="sales",
                     email="cl@gmail.com",
                     password=hash_password.create_hash("123456"),
                     is_admin=False),
                session,
            )

            # создаём админа
            admin_user = create_user(
                User(name="admin",
                     bank_position="app_owner",
                     bank_unit="app_development",
                     email="admin@mail.com",
                     password=hash_password.create_hash("123456"),
                     is_admin=True),
                session,
            )

    except Exception as e:
        raise
