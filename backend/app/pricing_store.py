# -*- coding: utf-8 -*-
"""
Единый источник цен диагностики (pricing.json в volume dao64_uploads).

Раньше DEFAULT_PRICING/PRICING_FILE были продублированы в routers/admin.py
и routers/pricing.py — то есть уже было два независимых места с одним и
тем же дефолтом. payments.py при этом вообще не знал об этом файле и
использовал отдельную захардкоженную цену (5500 ₽), пока лендинг и админка
показывали настоящую (14900 ₽) — отсюда расхождение.

Теперь все три места (admin.py, routers/pricing.py, routers/payments.py)
читают/пишут только через этот модуль.

── Два продукта ──────────────────────────────────────────────────────────────
Метод 3 продаётся по своей цене, Методы 1 и 2 — по общей. Поэтому файл
хранит два тарифных блока с одинаковым набором полей:

    {"m12": {...}, "m3": {...}}

Второй файл заводить не стали: это вернуло бы ровно ту дублирующуюся
конструкцию, ради устранения которой появился этот модуль.

Старый плоский формат (единственный тариф ключами верхнего уровня) читается
как m12 — на проде в файле лежит именно он, и переписывать его миграцией
незачем: он перезапишется при первом сохранении из админки.
"""
import os
from pathlib import Path

from app.json_store import read_json, write_json

# Каталог из UPLOAD_DIR — как в остальных модулях настроек. С зашитым путём
# тесты читали боевую цену и включённость оплаты.
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/var/www/64dao/uploads")
PRICING_FILE = Path(UPLOAD_DIR) / "pricing.json"

PRODUCTS = ("m12", "m3")
DEFAULT_PRODUCT = "m12"

DEFAULT_M12 = {
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

DEFAULT_M3 = {
    "title": "Матрица силы · Метод 3",
    "price": 20000,
    "currency": "₽",
    "description": "разовая оплата · НДС не облагается",
    "features": [
        {"label": "Диагностика", "value": "Метод 3 · матрица силы"},
        {"label": "Направлений в портфеле", "value": "От 3 до 8"},
        {"label": "PDF-отчёт", "value": "Включён"},
        {"label": "Онлайн-просмотр", "value": "Без ограничений"},
    ],
    "payment_enabled": False,
    "payment_note": "Оплата принимается картой и через СБП (Точка Банк). Сейчас идёт финальное тестирование платёжного шлюза — скоро включим приём платежей.",
}

DEFAULT_PRICING = {"m12": DEFAULT_M12, "m3": DEFAULT_M3}

# Признак старого формата: тариф лежал ключами верхнего уровня.
_LEGACY_MARKER = "price"


def _merge_product(defaults: dict, saved) -> dict:
    """Сохранённый блок поверх дефолтов. Ключ, добавленный в код, появляется
    у всех, а не только у тех, кто после этого пересохранил тариф в админке."""
    if not isinstance(saved, dict):
        return dict(defaults)
    return {**defaults, **saved}


def _normalise(raw: dict) -> dict:
    """Любой формат файла -> {'m12': {...}, 'm3': {...}}.

    read_json сливает с дефолтами только верхний уровень, поэтому слияние
    внутри блоков делаем здесь.
    """
    if _LEGACY_MARKER in raw and "m12" not in raw:
        # Плоский формат: весь файл — это тариф Методов 1 и 2.
        legacy = {k: v for k, v in raw.items() if k not in PRODUCTS}
        return {
            "m12": _merge_product(DEFAULT_M12, legacy),
            "m3": _merge_product(DEFAULT_M3, raw.get("m3")),
        }
    return {
        "m12": _merge_product(DEFAULT_M12, raw.get("m12")),
        "m3": _merge_product(DEFAULT_M3, raw.get("m3")),
    }


def read_pricing() -> dict:
    """Оба тарифных блока: {'m12': {...}, 'm3': {...}}."""
    return _normalise(read_json(PRICING_FILE))


def read_product(product: str = DEFAULT_PRODUCT) -> dict:
    """Один тарифный блок. Неизвестный продукт -> m12: не падаем на опечатке
    в query-параметре, но и не выдумываем третий тариф."""
    pricing = read_pricing()
    return pricing.get(product) or pricing[DEFAULT_PRODUCT]


def write_pricing(data: dict) -> None:
    """Сохранение с нормализацией.

    Нормализация на записи, а не только на чтении: PUT из админки принимает
    произвольный dict, и один кривой запрос иначе затирает структуру файла
    целиком. После нормализации в файле всегда оба блока со всеми полями.
    """
    write_json(PRICING_FILE, _normalise(data if isinstance(data, dict) else {}))


def current_price(product: str = DEFAULT_PRODUCT) -> float:
    """Текущая цена продукта в рублях (число)."""
    return float(read_product(product).get("price", 0))


def is_payment_enabled(product: str = DEFAULT_PRODUCT) -> bool:
    """Флаги оплаты у продуктов раздельные и могут расходиться: Методы 1 и 2
    уже продаются, Метод 3 ещё нет (или наоборот)."""
    return bool(read_product(product).get("payment_enabled", False))
