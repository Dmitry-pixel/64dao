# -*- coding: utf-8 -*-
"""
Тексты зон под одиночный режим Метода 3 (kind zone_reduced).

Идемпотентно: повторный запуск вставляет 0 и НЕ перетирает правки из админки.
Требует миграцию 036.

Две зоны из девяти в сокращённом отчёте лгут прямым текстом:
  high_low — «источник денег для остального портфеля»;
  mid_high — «останется одним из».
Остальные семь читаются нормально и своей версии не получают: резолюция
откатывается к kind zone (m3_service._zone_block).

Тексты утверждены владельцем 14 августа. Масштаб выровнен по остальным семи
зонам: тело около 200 знаков против медианных 166, а не 560, как в первой
редакции. Обе «типичные ошибки» переписаны под одиночный случай: общая
версия mid_high ссылалась на распределение ресурса между направлениями
и в одиночном отчёте лгала так же, как тело.

Запуск: docker compose exec -T backend python seed_m3_zone_reduced.py
"""
import asyncio

from sqlalchemy import select

import app.m3_models  # noqa: F401
from app.db import AsyncSessionLocal
from app.m3_models import M3Content

HIGH_LOW_BODY = (
    "Внутренний контур сильнее рынка: направление зарабатывает на "
    "исчерпанном спросе за счёт накопленной позиции. Это источник денег, "
    "а не точка роста: вопрос не куда его переложить, а на сколько "
    "его хватит."
)

HIGH_LOW_MISTAKE = (
    "Прочитать высокую конкурентную силу как основание вкладывать в рост "
    "здесь же, раз вкладывать больше некуда."
)

MID_HIGH_BODY = (
    "Рынок благоприятен, позиция достаточна для участия, но не для "
    "лидерства. Здесь и решается, доберёт ли направление силу до уровня "
    "рынка или окно закроется без него. Полумеры дороже обоих решений."
)

MID_HIGH_MISTAKE = (
    "Прочитать высокую привлекательность как запас времени: разрыв с теми, "
    "кто вкладывает, растёт каждый квартал."
)

ROWS = {
    # Название зоны не меняется: режим меняет разбор, а не карту.
    "high_low": ("Рынок исчерпан, удержание", HIGH_LOW_BODY, HIGH_LOW_MISTAKE),
    "mid_high": ("Незавершённое ядро", MID_HIGH_BODY, MID_HIGH_MISTAKE),
}


async def main() -> None:
    inserted = skipped = 0
    async with AsyncSessionLocal() as db:
        for key, (title, body, mistake) in ROWS.items():
            row = await db.scalar(select(M3Content).where(
                M3Content.kind == "zone_reduced",
                M3Content.key == key,
                M3Content.industry_id.is_(None),
            ))
            if row is not None:
                skipped += 1
                continue
            db.add(M3Content(kind="zone_reduced", key=key, industry_id=None,
                             title=title, body=body, mistake=mistake,
                             is_active=True))
            inserted += 1
        await db.commit()
    print("INSERTED=%d SKIPPED=%d" % (inserted, skipped))


if __name__ == "__main__":
    asyncio.run(main())
