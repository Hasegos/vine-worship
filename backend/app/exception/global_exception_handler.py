import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.core.paths import FRONTEND
from app.exception.api_exception_handler import api_error
from app.exception.business_exception import BusinessException

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory=FRONTEND / "template")


def error_response(
    request: Request, status: int, code: str, detail: str, headers: dict | None = None
) -> Response:
    """API에는 JSON, 웹 탐색에는 이스케이프한 오류 화면을 제공한다.

    Args:
        request: 현재 HTTP 요청.
        status: 응답 HTTP 상태 코드.
        code: 클라이언트가 구분할 오류 코드.
        detail: 비밀값을 포함하지 않는 사용자 설명.
        headers: 추가 HTTP 응답 헤더.
    Returns:
        API JSON 또는 웹 오류 템플릿 응답.
    """
    if request.url.path.startswith("/api/"):
        return api_error(status, code, detail, headers)
    return templates.TemplateResponse(
        request=request,
        name="error/404.html" if status == 404 else "error/500.html",
        context={"status": status, "detail": detail},
        status_code=status,
        headers=headers,
    )


def register_exception_handler(app: FastAPI) -> None:
    """구체적인 입력 오류와 전역 장애 처리를 앱에 연결한다.

    Args:
        app: 라우터와 예외 처리를 등록할 앱.
    """

    @app.exception_handler(BusinessException)
    async def business_error(request: Request, error: BusinessException) -> Response:
        """예상된 업무 오류를 내부 정보 없이 전달한다.

        Args:
            request: 현재 HTTP 요청.
            error: 분류할 예외.
        Returns:
            예상된 업무 오류 응답.
        """
        return error_response(request, error.status_code, error.code, error.detail)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> Response:
        """원본 입력 본문을 응답에 포함하지 않는다.

        Args:
            request: 현재 HTTP 요청.
            error: 분류할 예외.
        Returns:
            입력 본문을 노출하지 않는 검증 오류 응답.
        """
        return error_response(request, 422, "INVALID_INPUT", "요청 값의 형식을 확인해 주세요.")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException) -> Response:
        """404 등 HTTP 오류도 같은 계약으로 반환한다.

        Args:
            request: 현재 HTTP 요청.
            error: 분류할 예외.
        Returns:
            HTTP 상태와 헤더를 보존한 오류 응답.
        """
        return error_response(
            request, error.status_code, "HTTP_ERROR", str(error.detail), error.headers
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, error: SQLAlchemyError) -> Response:
        """연결 문자열·SQL·바이너리 인자를 로그와 응답에 노출하지 않는다.

        Args:
            request: 현재 HTTP 요청.
            error: 분류할 예외.
        Returns:
            연결 정보를 숨긴 503 오류 응답.
        """
        logger.error("Database request failed: %s", type(error).__name__)
        return error_response(
            request,
            503,
            "DATABASE_UNAVAILABLE",
            "DB에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.",
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception) -> Response:
        """분류되지 않은 장애의 내부 내용을 숨긴다.

        Args:
            request: 현재 HTTP 요청.
            error: 분류할 예외.
        Returns:
            내부 정보를 숨긴 500 오류 응답.
        """
        logger.error("Unhandled request failure: %s", type(error).__name__)
        return error_response(request, 500, "INTERNAL_ERROR", "처리 중 오류가 발생했습니다.")