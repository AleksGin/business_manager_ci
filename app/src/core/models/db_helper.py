from typing import AsyncGenerator

from app.src.core.config import settings
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.asyncio.session import AsyncSession


class Db_Helper:
    def __init__(
        self,
        url: str,
        echo: bool = False,
        echo_pool: bool = False,
        max_overflow: int = 10,
        pool_size: int = 5,
    ) -> None:
        self.async_engine = create_async_engine(
            url=url,
            echo=echo,
            echo_pool=echo_pool,
            max_overflow=max_overflow,
            pool_size=pool_size,
        )
        self.session_factory = async_sessionmaker(
            bind=self.async_engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    async def engine_dispose(self) -> None:
        await self.async_engine.dispose()

    async def session_getter(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            yield session


DbHelper = Db_Helper(
    url=settings.db_config.url,
    echo=settings.db_config.echo,
    echo_pool=settings.db_config.echo_pool,
    max_overflow=settings.db_config.max_overflow,
    pool_size=settings.db_config.pool_size,
)
