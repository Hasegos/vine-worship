from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """내부 예외나 연결 비밀값을 노출하지 않는 오류."""

    code: str
    detail: str