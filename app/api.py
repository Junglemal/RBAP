from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from database.database import init_db
from database.config import get_settings
from services.logging.logging import get_logger
from routes.home import home_route
from routes.user import user_route
from routes.event import event_route
from routes.parser import parser_route
from routes.ml import ml_route
from typing import Dict, List, Optional, Any
# from api_analytics.fastapi import Analytics


logger = get_logger(logger_name=__name__)
settings = get_settings()

def create_application() -> FastAPI:
    """
    Create and configure FastAPI application.
    Returns:
        FastAPI: Configured application instance
    """

    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.API_VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )

    # возможность добавления аналитики
    # app.add_middleware(Analytics, api_key="----")  # Добавление промежуточного слоя

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Регистрируем rout-ы
    app.include_router(home_route, tags=['Home'])
    app.include_router(ml_route, prefix='/api/ml', tags=['ML'])
    app.include_router(user_route, prefix='/api/users', tags=['Users'])
    # app.include_router(event_route, prefix='/api/events', tags=['Events'])
    app.include_router(parser_route, prefix="/api/parser", tags=["Parser"])

    return app

app = create_application()

@app.on_event("startup")
def on_startup():
    try:
        logger.info("Initializing database...")
        init_db(drop_all=False)
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Application shutting down...")


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    uvicorn.run(
        'api:app',
        host='0.0.0.0',
        port=8080,
        reload=True,
        log_level="info"
    )
