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
import time

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

from app.config import get_settings
from app.tochka_settings import get_jwt_token

settings = get_settings()

TOCHKA_PUBLIC_KEY_URL = "https://enter.tochka.com/doc/openapi/static/keys/public"
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

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(TOCHKA_PUBLIC_KEY_URL)
        resp.raise_for_status()
        jwk_dict = resp.json()

    public_key = RSAAlgorithm.from_jwk(jwk_dict)
    _public_key_cache["key"] = public_key
    _public_key_cache["fetched_at"] = now
    return public_key


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
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.base_url}/uapi/acquiring/v1.0/payments_with_receipt",
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_payment_status(self, operation_id: str) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.base_url}/uapi/acquiring/v1.0/payments/{operation_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def refund_payment(self, operation_id: str, amount: float | None = None) -> dict:
        """
        Возврат платежа, принятого через интернет-эквайринг.
        https://developers.tochka.com/docs/tochka-api/api/refund-payment-operation-acquiring-v-1-0-payments-operation-id-refund-post
        Если amount не передан — предполагается полный возврат (уточнить в доках
        точное поведение при отсутствии тела запроса).
        """
        payload = {"Data": {"amount": amount}} if amount is not None else {}
        async with httpx.AsyncClient(timeout=15.0) as client:
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
