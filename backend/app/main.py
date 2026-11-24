from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.controller.asset_controller import router as asset_router
from app.controller.home_controller import router as home_router
from app.controller.score_controller import router as score_router
from app.core.config import settings
from app.core.paths import FRONTEND
from app.core.logging import configure_logging
from app.db.session import engine, initialize_database
from app.exception.global_exception_handler import register_exception_handler
from app.repository.score_repository import source_score

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; font-src 'self' data:; connect-src 'self'; "
    "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """기존 DB를 변경하지 않고 신규 테이블을 준비하며 종료 시 연결을 정리한다.

    Args:
        app: 라우터와 예외 처리를 등록할 앱.
    """
    configure_logging()
    source_score()
    try:
        await initialize_database()
        yield
    finally:
        await engine().dispose()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan, docs_url=None, redoc_url=None)
register_exception_handler(app)
app.include_router(home_router)
app.include_router(score_router)
app.include_router(asset_router)
app.mount("/static", StaticFiles(directory=FRONTEND / "static"), name="static")
app.mount("/vendor/osmd", StaticFiles(directory=FRONTEND / "vendor/osmd"), name="osmd")


@app.get("/api/health")
async def health() -> dict[str, str]:
    """컨테이너가 실제 DB 쿼리를 수행할 수 있는지 확인한다.

    Returns:
        앱과 PostgreSQL의 연결 상태.
    """
    async with engine().connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "postgresql"}


@app.middleware("http")
async def response_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """화면·파일 응답의 외부 리소스 호출과 캐시를 제한한다.

    Args:
        request: 현재 HTTP 요청.
        call_next: 다음 요청 처리기.
    Returns:
        보안·캐시 헤더를 적용한 응답.
    """
    response = await call_next(request)
    response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response