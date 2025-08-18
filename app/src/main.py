from contextlib import asynccontextmanager

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from db import DbHelper
from evaluations.routers import evaluations_router
from tasks.routers import tasks_router
from teams.routers import (
    members_router,
    teams_router,
)
from users.routers import (
    auth_router,
    users_router,
)
from meetings.routers import meetings_router
from calendars.routers import calendar_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown
    print("dispose engine")
    await DbHelper.engine_dispose()


def create_app() -> FastAPI:
    """Фабрика для создания FastAPI приложения"""

    app = FastAPI(
        title="Business Managment System",
        description="MVP система управления командами и задачами",
        version="1.0",
        lifespan=lifespan,
    )

    app.mount(
        "/static",
        StaticFiles(directory="static"),
        name="static",
    )

    # CORS middleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Auth роутеры
    app.include_router(
        auth_router,
        prefix=settings.api_prefix.auth,
        tags=["Аутентификация"],
    )

    # Users роутеры
    app.include_router(
        users_router,
        prefix=settings.api_prefix.user,
        tags=["Пользователи"],
    )

    # Teams роутеры
    app.include_router(
        teams_router,
        prefix="/api/teams",
        tags=["Команды"],
    )

    app.include_router(
        members_router,
        prefix="/api/teams",
        tags=["Участники команд"],
    )

    # Tasks роутеры
    app.include_router(
        tasks_router,
        prefix="/api/tasks",
        tags=["Задачи"],
    )

    # Evaluations роутеры
    app.include_router(
        evaluations_router,
        prefix="/api/evaluations",
        tags=["Оценки"],
    )

    # Meetings роутеры
    app.include_router(
        meetings_router,
        prefix="/api/meetings",
        tags=["Встречи"],
    )

    # Calendar роутеры
    app.include_router(
        calendar_router,
        prefix="/api/calendar",
        tags=["Календарь"],
    )

    @app.get("/", response_class=FileResponse)
    async def read_index() -> FileResponse:
        return FileResponse("index.html")

    @app.get("/api")
    async def root():
        """Главная страница"""
        return {"message": "Business Manager", "docs": "/docs", "version": "1.0"}

    @app.get("/health")
    async def health_check():
        """Проверка здоровья приложения"""
        return {"status": "ok"}

    return app


# Создание экземпляра приложения
app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        app="main:app",
        host=settings.app_config.host,
        port=settings.app_config.port,
        reload=settings.app_config.reload_mode,
    )
