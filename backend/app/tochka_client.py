"""
Клиент для API интернет-эквайринга Точка Банка.

Документация: https://developers.tochka.com/docs/tochka-api/
Авторизация: JWT (интеграция для себя, без OAuth-провижининга пользователям).

ВАЖНО (не подтверждено, требует уточнения при получении доступа к ЛК):
  - механизм подписи вебхуков (заголовок с HMAC/JWT) — сейчас verify_webhook
    является no-op заглушкой, см. TODO ниже.
  - формат обновления JWT (статический токен vs refresh) — сейчас
    предполагается статический долгоживущий токен из .env.
"""
import httpx
from app.config import get_settings

settings = get_settings()


class TochkaClient:
    def __init__(self):
        self.base_url = settings.tochka_api_base_url
        self.customer_code = settings.tochka_customer_code
        self.merchant_id = settings.tochka_merchant_id
        self.token = settings.tochka_jwt_token

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
        customer_email: str | None = None,
    ) -> dict:
        payload = {
            "Data": {
                "customerCode": self.customer_code,
                "amount": str(amount),
                "purpose": purpose,
                "redirectUrl": "https://64dao.ru/purchases",
                "failRedirectUrl": "https://64dao.ru/purchases?status=failed",
                "merchantId": self.merchant_id,
                "consumerId": order_id,
                "Client": {"email": customer_email} if customer_email else {},
            }
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.base_url}/uapi/acquiring/v1.0/payments",
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

    def verify_webhook(self, headers: dict, body: bytes) -> bool:
        """
        TODO: реализовать проверку подписи после уточнения механизма в ЛК Точки.
        Сейчас — заглушка, ВСЕГДА возвращает True.
        НЕ включать enforce_credits=true в проде, пока это не реализовано.
        """
        return True


def get_tochka_client() -> TochkaClient:
    return TochkaClient()
