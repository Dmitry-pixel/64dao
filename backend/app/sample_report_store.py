# -*- coding: utf-8 -*-
"""
Пути к файлам примеров отчёта.

Примеров два: один на Методы 1 и 2 (продаются одним тарифом и показываются
одним блоком лендинга), второй на Метод 3. Ключ — тот же, что у тарифов
в pricing_store: "m12" и "m3". Заводить третий словарь названий продуктов
не стали.

Путь берётся из UPLOAD_DIR, как в остальных модулях: с зашитым путём тесты
писали бы в боевой каталог.
"""
import os
from pathlib import Path

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/var/www/64dao/uploads")

# Имя файла Методов 1 и 2 оставлено прежним: на проде он уже лежит,
# переименование потребовало бы миграции файла ради ничего.
FILES = {
    "m12": Path(UPLOAD_DIR) / "sample_report.pdf",
    "m3": Path(UPLOAD_DIR) / "sample_report_m3.pdf",
    # Описание методологии — не пример отчёта, а отдельный документ. Слот заведён
    # здесь, а не отдельным модулем: хранение, загрузка и выдача у него ровно те
    # же, отличаются только имя файла и подпись в админке.
    "methodology": Path(UPLOAD_DIR) / "methodology_64dao.pdf",
}

DOWNLOAD_NAMES = {
    "m12": "Example_report_64DAO.pdf",
    "m3": "Example_report_64DAO_Method3.pdf",
    "methodology": "Methodology_64DAO.pdf",
}

DEFAULT_PRODUCT = "m12"

# Лендинг и админка оперируют номером метода, бэкенд — кодом продукта.
_BY_METHOD = {
    "1": "m12", "2": "m12", "12": "m12", "3": "m3",
    "methodology": "methodology",
}


def product_for(method: str | None) -> str:
    """Номер метода из query -> код продукта. Неизвестное значение -> m12:
    не падаем на опечатке в ссылке и не выдумываем третий пример."""
    if method is None:
        return DEFAULT_PRODUCT
    return _BY_METHOD.get(str(method).strip(), DEFAULT_PRODUCT)


def file_for(method: str | None) -> Path:
    return FILES[product_for(method)]


def download_name_for(method: str | None) -> str:
    return DOWNLOAD_NAMES[product_for(method)]
