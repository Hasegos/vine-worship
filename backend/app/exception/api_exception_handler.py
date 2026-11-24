from fastapi.responses import JSONResponse
from app.schema.error_schema import ErrorResponse


def api_error(
    status_code: int, code: str, detail: str, headers: dict | None = None
) -> JSONResponse:
    """정상 응답과 구분 가능한 오류 계약을 유지한다."""
    return JSONResponse(
        ErrorResponse(code=code, detail=detail).model_dump(),
        status_code=status_code,
        headers=headers,
    )