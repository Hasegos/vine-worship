from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """명시적으로 생성할 테이블 메타데이터를 모은다."""