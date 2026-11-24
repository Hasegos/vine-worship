from fastapi.responses import JSONResponse
from app.schema.error_schema import ErrorResponse


def api_error(
    status_code: int, code: str, detail: str, headers: dict | None = None
) -> JSONResponse:
    """정상 응답과 구분 가능한 오류 계약을 유지한다.

    Args:
        status_code: 사용자에게 전달할 HTTP 상태 코드.
        code: 클라이언트가 구분할 오류 코드.
        detail: 비밀값을 포함하지 않는 사용자 설명.
        headers: 추가 HTTP 응답 헤더.
    Returns:
        공통 code·detail 형식의 JSON 오류 응답.
    """
    return JSONResponse(
        ErrorResponse(code=code, detail=detail).model_dump(),
        status_code=status_code,
        headers=headers,
    )