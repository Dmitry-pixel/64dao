from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Пересобирать PDF при каждом скачивании.
    # False — отдавать сохранённый файл (используется в тестах: иначе каждый
    # вызов скачивания поднимает Chromium и прогон растягивается на минуты).
    regenerate_pdf_on_download: bool = True
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
    support_email: str = ""      # куда слать сообщения с формы обратной связи

    @property
    def smtp_from_address(self) -> str:
        """Адрес отправителя: smtp_from если задан, иначе smtp_user."""
        return self.smtp_from or self.smtp_user

    @property
    def support_email_address(self) -> str:
        """Адрес получателя обратной связи: support_email, иначе smtp_from_address."""
        return self.support_email or self.smtp_from_address

    # ── OTP ───────────────────────────────────────────────────────────────────
    otp_expire_minutes: int = 10

    # ── App ───────────────────────────────────────────────────────────────────
    # rstrip("/") применяется при использовании — защита от trailing slash в .env
    app_url: str = "https://64dao.ru"
    admin_setup_key: str = ""

    # ── Storage ───────────────────────────────────────────────────────────────
    uploads_dir: str = "/var/www/64dao/uploads/reports"

    # ── Payments (feature flags) ─────────────────────────────────────────────
    # До подключения реальной платёжной системы credits-проверка отключена
    # по умолчанию (создание completed-assessment не блокируется). Когда
    # платёжный шлюз будет готов и вебхук проверен тестовой отправкой —
    # переключить ENFORCE_CREDITS=true в .env.
    enforce_credits: bool = False

    # ── Финансовый блок Метода 1 (feature flag) ──────────────────────────────
    # Жёсткая обязательность finance_answers для completed-диагностики Метода 1.
    # По умолчанию False: старый фронт без финблока работает, финрезультат пуст.
    # Включить (FINANCE_BLOCK_REQUIRED=true) синхронно с новым фронтом (Этап 6).
    finance_block_required: bool = False
    # ── Email-напоминания (PR6) ──
    reminders_enabled: bool = True          # kill-switch для cron-джоба
    repeat_reminder_days: int = 90          # через сколько дней «пора повторить»

    # ── Tochka Bank API ───────────────────────────────────────────────────────
    tochka_api_base_url: str = "https://enter.tochka.com"
    tochka_customer_code: str = ""     # Get Customers List → customerType: Business
    tochka_merchant_id: str = ""       # Get Retailers → merchantId торговой точки МСС 7299
    tochka_jwt_token: str = ""         # ЛК Точки → Сервисы → Интеграции и API → Сгенерировать JWT
    tochka_webhook_secret: str = ""    # НЕ используется в новой схеме проверки (см. ниже) —
                                        # оставлено для обратной совместимости, можно удалить.

    # Путь к CA-бандлу для проверки TLS-сертификата enter.tochka.com.
    # Бандл (стандартные CA + Минцифры) собирается в backend/Dockerfile,
    # значение по умолчанию приходит из ENV TOCHKA_CA_BUNDLE того же образа.
    # Пустая строка или несуществующий файл -> дефолтное хранилище httpx.
    tochka_ca_bundle: str = ""

    # Налоговый режим для чека (54-ФЗ). ИП на УСН доходы.
    tochka_tax_system_code: str = "usn_income"  # osn | usn_income | usn_income_outcome | esn | patent
    # Ставка НДС в чеке НЕ здесь — см. app/tax_settings.py (переключатель
    # vat_enabled в tax_settings.json, меняется без редеплоя). Сейчас ИП
    # освобождён от НДС (доход не превышает лимит по УСН).

    # За сколько дней до истечения выпускающего CA НУЦ Минцифры слать письмо.
    # Проверку запускает host cron: deploy/scripts/check-ca-expiry.sh.
    ca_expiry_warn_days: int = 60

    # ── Метод 3 «Матрица силы» (feature flag) ────────────────────────────────
    # При false роутер зарегистрирован, но эндпоинты отдают 404, а пункты меню
    # скрыты. Позволяет катить код на прод, не открывая функциональность.
    # Порядок открытия: сначала M3_ENABLED=true и обкатка под админским
    # доступом на портфелях пилота, и только затем снятие заглушки входа.
    m3_enabled: bool = False

    # ── Debug ─────────────────────────────────────────────────────────────────
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
