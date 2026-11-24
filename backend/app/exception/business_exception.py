class BusinessException(Exception):
    """사용자에게 전달할 상태 코드와 안전한 설명을 가진다."""

    def __init__(self, detail: str, status_code: int = 422, code: str = "INVALID_INPUT") -> None:
        """외부에 전달할 업무 오류의 상태와 설명을 보관한다.

        Args:
            detail: 비밀값을 포함하지 않는 사용자 설명.
            status_code: 사용자에게 전달할 HTTP 상태 코드.
            code: 클라이언트가 구분할 오류 코드.
        """
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.code = code