"""
Единый источник цены диагностики (pricing.json в volume dao64_uploads).

Раньше DEFAULT_PRICING/PRICING_FILE были продублированы в routers/admin.py
и routers/pricing.py — то есть уже было два независимых места с одним и
тем же дефолтом. payments.py при этом вообще не знал об этом файле и
использовал отдельную захардкоженную цену (5500 ₽), пока лендинг и админка
показывали настоящую (14900 ₽) — отсюда расхождение.

Теперь все три места (admin.py, routers/pricing.py, routers/payments.py)
читают/пишут только через этот модуль.
"""
import os
from pathlib import Path

from app.json_store import read_json, write_json

# Каталог из UPLOAD_DIR — как в остальных модулях настроек. С зашитым путём
# тесты читали боевую цену и включённость оплаты.
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/var/www/64dao/uploads")
PRICING_FILE = Path(UPLOAD_DIR) / "pricing.json"

DEFAULT_PRICING = {
    "title": "Полный отчёт 64 ДАО",
    "price": 14900,
    "currency": "₽",
    "description": "разовая оплата · НДС не облагается",
    "features": [
        {"label": "Диагностика", "value": "Метод 1 + Метод 2"},
        {"label": "PDF-отчёт", "value": "Включён"},
        {"label": "Онлайн-просмотр", "value": "Без ограничений"},
        {"label": "Срок готовности", "value": "До 30 минут"},
    ],
    "payment_enabled": False,
    "payment_note": "Оплата принимается картой и через СБП (Точка Банк). Сейчас идёт финальное тестирование платёжного шлюза — скоро включим приём платежей.",
}


def read_pricing() -> dict:
    # Дефолты подмешиваются: ключ, добавленный в код, появляется у всех, а не
    # только у тех, кто после этого пересохранил тариф в админке.
    return read_json(PRICING_FILE, DEFAULT_PRICING)


def write_pricing(data: dict) -> None:
    write_json(PRICING_FILE, data)


def current_price() -> float:
    """Текущая цена диагностики в рублях (число)."""
    pricing = read_pricing()
    return float(pricing.get("price", DEFAULT_PRICING["price"]))


def is_payment_enabled() -> bool:
    return bool(read_pricing().get("payment_enabled", False))
