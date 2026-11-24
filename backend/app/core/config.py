from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL
from sqlalchemy.engine import make_url

from app.core.paths import ROOT


class Settings(BaseSettings):
    """환경변수와 루트 .env에서 읽은 실행 설정. 비밀값은 표현에서 숨긴다."""

    PROJECT_NAME: str = "Vine Worship"
    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr = Field(repr=False)
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535)
    DATABASE_URL: SecretStr | None = Field(default=None, repr=False)
    POOL_SIZE: int = Field(default=5, ge=1)
    UPLOAD_CONCURRENCY: int = Field(default=2, ge=1, le=10)
    UPLOAD_CHUNK_SIZE: int = Field(default=1024 * 1024, ge=1024, le=16 * 1024 * 1024)

    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True
    )

    @property
    def database_url(self) -> URL:
        """특수문자 비밀번호를 안전하게 처리한 PostgreSQL 연결 정보를 만든다.

        Returns:
            특수문자를 안전하게 처리한 PostgreSQL 연결 정보.
        Raises:
            ValueError: DATABASE_URL이 PostgreSQL psycopg 연결 형식이 아닌 경우.
        """
        if self.DATABASE_URL:
            url = make_url(self.DATABASE_URL.get_secret_value())
            if url.drivername != "postgresql+psycopg":
                raise ValueError("DATABASE_URL은 postgresql+psycopg 형식이어야 합니다.")
            return url
        return URL.create(
            "postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD.get_secret_value(),
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        )


settings = Settings()