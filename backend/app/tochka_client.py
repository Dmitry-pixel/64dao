"""
Клиент для API интернет-эквайринга Точка Банка.

Документация: https://developers.tochka.com/docs/tochka-api/
Авторизация: JWT (интеграция для себя, без OAuth-провижининга пользователям).

Изменения к предыдущей версии:
  1. verify_webhook переименован в verify_and_decode_webhook и реализован по-настоящему:
     тело вебхука — НЕ JSON, а «голая» строка JWT (RS256), см.
     https://developers.tochka.com/docs/tochka-api/opisanie-metodov/vebhuki/#public-key
  2. create_payment_with_receipt переведён на реальный endpoint /payments_with_receipt
     и теперь передаёт обязательные поля paymentMode, Items, Client.email,
     taxSystemCode — без них Точка отвечала бы 400 (эти поля required в схеме).
"""
import logging
import os
import time

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

from app.config import get_settings
from app.tochka_settings import get_jwt_token

logger = logging.getLogger(__name__)

settings = get_settings()

TOCHKA_PUBLIC_KEY_URL = "https://enter.tochka.com/doc/openapi/static/keys/public"


def _resolve_ca_bundle() -> str | bool:
    """Что передавать в httpx verify= для вызовов к Точке.

    Бандл (стандартные CA + корневой и выпускающий Минцифры) собирается в
    backend/Dockerfile, путь приходит из ENV TOCHKA_CA_BUNDLE. Нужен на случай
    перехода Точки с TrustAsia на НУЦ Минцифры: этого CA нет ни в certifi,
    ни в ca-certificates Debian.

    Возврат True = дефолтное хранилище. Это фолбэк, а не «выключить проверку»:
    verify=False здесь недопустим — JWT банка уходит в заголовке Authorization,
    соединение без проверки цепочки означает риск утечки токена.
    """
    path = (settings.tochka_ca_bundle or "").strip()
    if not path:
        logger.warning(
            "TOCHKA_CA_BUNDLE не задан — используется дефолтное хранилище CA. "
            "См. backend/certs/README.md"
        )
        return True
    if not os.path.isfile(path):
        logger.error(
            "TOCHKA_CA_BUNDLE=%s не существует — откат на дефолтное хранилище CA. "
            "Проверьте, что образ пересобран (docker compose build backend), "
            "а не только перезапущен.",
            path,
        )
        return True
    return path


# Считается один раз при импорте: путь в рантайме не меняется, а os.path.isfile
# на каждый запрос — лишний syscall. После правки .env нужен рестарт контейнера.
TOCHKA_SSL_VERIFY: str | bool = _resolve_ca_bundle()
_PUBLIC_KEY_TTL_SECONDS = 3600  # раз в час; ключ может обновляться на стороне Точки

_public_key_cache: dict = {"key": None, "fetched_at": 0.0}


async def _get_tochka_public_key():
    """Получает и кэширует публичный ключ Точки для проверки подписи вебхуков.

    Ключ не хардкодим в коде (см. предупреждение в доках Точки — «в рабочей
    интеграции лучше получать ключ по ссылке, чтобы он не устарел»).
    """
    now = time.time()
    if _public_key_cache["key"] and now - _public_key_cache["fetched_at"] < _PUBLIC_KEY_TTL_SECONDS:
        return _public_key_cache["key"]

    async with httpx.AsyncClient(timeout=10.0, verify=TOCHKA_SSL_VERIFY) as client:
        resp = await client.get(TOCHKA_PUBLIC_KEY_URL)
        resp.raise_for_status()
        jwk_dict = resp.json()

    public_key = RSAAlgorithm.from_jwk(jwk_dict)
    _public_key_cache["key"] = public_key
    _public_key_cache["fetched_at"] = now
    return public_key


def extract_operation(resp: dict) -> dict:
    """Первая операция из ответа Get Payment Operation Info.

    Формат — Data.Operation[] (список), а не Data напрямую. В
    get_order_status читалось resp["Data"]["status"], то есть всегда None:
    запасной путь «вебхук не дошёл, спросим статус» не работал вообще, и
    заказ с потерянным вебхуком навсегда оставался pending. Проверено на
    боевой операции 662a3212.

    Функция модульного уровня, а не метод клиента: разбор ответа не зависит
    от состояния соединения, а в тестах клиент подменяется AsyncMock —
    вызов через него вернул бы корутину вместо словаря.
    """
    ops = (resp or {}).get("Data", {}).get("Operation") or []
    return ops[0] if ops else {}


class TochkaClient:
    def __init__(self):
        self.base_url = settings.tochka_api_base_url
        self.customer_code = settings.tochka_customer_code
        self.merchant_id = settings.tochka_merchant_id
        # Токен теперь редактируется из админки (tochka_settings.json),
        # .env — только запасной вариант, если админка ещё не использовалась.
        self.token = get_jwt_token()

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def create_payment_with_receipt(
        self,
        amount: float,
        purpose: str,
        order_id: str,
        customer_email: str,
        items: list[dict],
        payment_mode: list[str] | None = None,
    ) -> dict:
        """
        Создаёт платёжную ссылку с чеком (фискализация 54-ФЗ).

        items — список товарных позиций, каждый элемент:
          {
            "name": str,                 # required, <= 256 символов
            "amount": float,              # required, цена за единицу
            "quantity": float,            # required
            "vatType": str,                # "none" | "vat0" | "vat5" | "vat7" |
                                            # "vat10" | "vat20" | "vat105" | "vat107" |
                                            # "vat110" | "vat120" — берём из app.tax_settings.current_vat_type()
            "paymentMethod": "full_prepayment",  # т.к. оплата предшествует выдаче отчёта
            "paymentObject": "service",           # отчёт — услуга, не товар
          }

        customer_email обязателен — без него Точка отклонит запрос (Client.email required).

        merchantId — необязательное поле (по документации Точки: если у вас
        одна торговая точка, можно не передавать). Отправляем его только если
        задан в settings — пустая строка не проходит валидацию (minLength 15).
        """
        data = {
            "customerCode": self.customer_code,
            "amount": amount,
            "purpose": purpose,
            "redirectUrl": "https://64dao.ru/purchases",
            "failRedirectUrl": "https://64dao.ru/purchases?status=failed",
            "paymentMode": payment_mode or ["card", "sbp"],
            "paymentLinkId": order_id,  # номер заказа — именно сюда, не в consumerId
            "taxSystemCode": settings.tochka_tax_system_code,
            "Client": {"email": customer_email},
            "Items": items,
        }
        if self.merchant_id:
            data["merchantId"] = self.merchant_id

        payload = {"Data": data}
        async with httpx.AsyncClient(timeout=15.0, verify=TOCHKA_SSL_VERIFY) as client:
            resp = await client.post(
                f"{self.base_url}/uapi/acquiring/v1.0/payments_with_receipt",
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_payment_status(self, operation_id: str) -> dict:
        async with httpx.AsyncClient(timeout=15.0, verify=TOCHKA_SSL_VERIFY) as client:
            resp = await client.get(
                f"{self.base_url}/uapi/acquiring/v1.0/payments/{operation_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def refund_payment(self, operation_id: str, amount: float) -> dict:
        """
        Возврат платежа, принятого через интернет-эквайринг.
        https://developers.tochka.com/docs/tochka-api/api/refund-payment-operation-acquiring-v-1-0-payments-operation-id-refund-post
        Если amount не передан — предполагается полный возврат (уточнить в доках
        точное поведение при отсутствии тела запроса).
        """
        # Data обязателен всегда: на пустом теле Точка отвечает 400
        # "Field Data : Field required" (воспроизведено на боевом возврате
        # тестового платежа 1 ₽). Рабочее тело — {"Data": {"amount": N}}.
        payload = {"Data": {"amount": float(amount)}}
        async with httpx.AsyncClient(timeout=15.0, verify=TOCHKA_SSL_VERIFY) as client:
            resp = await client.post(
                f"{self.base_url}/uapi/acquiring/v1.0/payments/{operation_id}/refund",
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def verify_and_decode_webhook(self, raw_body: bytes) -> dict:
        """
        Проверяет подпись вебхука (JWT RS256, публичный ключ Точки) и
        возвращает расшифрованные claims (плоский dict: operationId, status,
        amount, merchantId, paymentLinkId, consumerId, webhookType, ...).

        ВАЖНО: тело вебхука — НЕ JSON. Content-Type: text/plain, в теле
        «голая» строка JWT. Раньше код делал request.json() — это упало бы
        на первом же реальном вебхуке.

        Бросает jwt.InvalidTokenError (и подклассы), если подпись неверна
        или токен повреждён — вызывающий код должен вернуть 401.
        """
        token = raw_body.decode("utf-8").strip()
        public_key = await _get_tochka_public_key()
        claims = jwt.decode(
            token,
            key=public_key,
            algorithms=["RS256"],
            options={"verify_exp": False, "verify_aud": False},
        )
        return claims


def get_tochka_client() -> TochkaClient:
    return TochkaClient()
