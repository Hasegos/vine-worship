import logging


def configure_logging() -> None:
    """파일 대신 컨테이너 표준 출력으로 운영 로그를 모은다."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")