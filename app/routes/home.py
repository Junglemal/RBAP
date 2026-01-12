from typing import Dict
from fastapi import APIRouter, HTTPException


home_route = APIRouter()

@home_route.get(
    "/",
    response_model=Dict[str, str],
    summary="Root endpoint",
    description="Returns a welcome message"
)
async def index() -> str:
    """Приветственное слово"""
    try:
        return {"message": "Рады приветстовать Вас на платформе анализа отзывов!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@home_route.get(
    "/health",
    response_model=Dict[str, str],
    summary="Health check endpoint",
    description="Returns service health status"
)
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint for monitoring.
    Returns:
        Dict[str, str]: Health status message
    Raises:
        HTTPException: If service is unhealthy
    """
    try:
        # Add actual health checks here
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail="Service unavailable"
        )
