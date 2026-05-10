from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    db_user: str
    db_pass: str
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "dao64"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.db_user}:{self.db_pass}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_url_sync(self) -> str:
        """Для Alembic (синхронный драйвер psycopg2)."""
        return (
            f"postgresql+psycopg2://"
            f"{self.db_user}:{self.db_pass}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # ── JWT ───────────────────────────────────────────────────────────────────
    jwt_secret: str          # ≥ 32 символа
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7

    # ── SMTP ──────────────────────────────────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = 465         # 465 = SSL/TLS, 587 = STARTTLS
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = ""          # если пусто — используется smtp_user
    smtp_use_tls: bool = True    # True для порта 465, False для 587

    @property
    def smtp_from_address(self) -> str:
        """Адрес отправителя: smtp_from если задан, иначе smtp_user."""
        return self.smtp_from or self.smtp_user

    # ── OTP ───────────────────────────────────────────────────────────────────
    otp_expire_minutes: int = 10

    # ── App ───────────────────────────────────────────────────────────────────
    # rstrip("/") применяется при использовании — защита от trailing slash в .env
    app_url: str = "https://64dao.ru"
    admin_setup_key: str = ""

    # ── Storage ───────────────────────────────────────────────────────────────
    uploads_dir: str = "/var/www/64dao/uploads/reports"

    # ── Debug ─────────────────────────────────────────────────────────────────
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
