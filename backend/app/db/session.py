from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base


@lru_cache(maxsize=1)
def engine() -> AsyncEngine:
    """비밀값을 숨긴 PostgreSQL 연결 풀을 제공한다."""
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 5},
        pool_size=settings.POOL_SIZE,
        max_overflow=0,
    )


def session_factory() -> async_sessionmaker:
    """요청별 세션을 만들며 ORM 결과를 커밋 뒤에도 읽을 수 있게 한다."""
    return async_sessionmaker(engine(), expire_on_commit=False)


async def initialize_database() -> None:
    """등록된 신규 테이블만 생성한다. migration과 기존 스키마 변경은 수행하지 않는다."""
    from app.model.asset_model import AssetModel
    from app.model.asset_chunk_model import AssetChunkModel

    async with engine().begin() as connection:
        await connection.run_sync(Base.metadata.create_all)