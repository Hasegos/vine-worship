class BusinessException(Exception):
    """사용자에게 전달할 상태 코드와 안전한 설명을 가진다."""

    def __init__(self, detail: str, status_code: int = 422, code: str = "INVALID_INPUT") -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.code = code