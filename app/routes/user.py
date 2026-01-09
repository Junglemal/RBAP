from fastapi import APIRouter, Depends, HTTPException, status
from auth.hash_password import HashPassword
from database.database import get_session
from services.crud import user_crud as UserService
from models.user import User
from typing import List, Dict, Any
import logging


# Configure logging
logger = logging.getLogger(__name__)

user_route = APIRouter()
hash_password = HashPassword()

@user_route.post('/signup',
                 status_code=status.HTTP_201_CREATED,
                 summary="User Registration",
                 description="Register a new user with email and password")

async def signup(user: User, session=Depends(get_session)) -> Dict[str, str]:
    """регистрация пользователей"""
    try:
        # если пользователь существует, возвращаем исключение
        if UserService.get_user_by_email(user.email, session):
            logger.warning(f"Signup attempt with existing email: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
        # хэшируем пароль
        hashed_password = hash_password.create_hash(user.password)
        user.password = hashed_password
        UserService.create_user(user, session)

        return {"message": "User created successfully"}

    except Exception as e:
        logger.error(f"Error during signup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user"
        )


@user_route.post('/signin')
async def signin(data: User, session=Depends(get_session)) -> dict:
    """авторизация пользователей"""
    user = UserService.get_user_by_email(data.email, session)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User does not exist!')

    if not hash_password.verify_hash(data.password, user.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Wrong credentials passed!')

    return {'message': 'User signed in successfully.', 'is_admin': user.is_admin}


@user_route.get(
    "/get_all_users",
    response_model=List[User],
    summary="Get all users",
    response_description="List of all users"
)
async def get_all_users(session=Depends(get_session)) -> List[User]:
    """получаем список всех пользователей сервиса"""
    try:
        users = UserService.get_all_users(session)
        logger.info(f"Retrieved {len(users)} users")
        return users
    except Exception as e:
        logger.error(f"Error retrieving users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving users"
        )
