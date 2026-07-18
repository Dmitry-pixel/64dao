# -*- coding: utf-8 -*-
"""
Заголовки правил напряжений R1–R12 (fin_content, kind=tension_rule).
Обновляет только title в payload; text и condition не трогает. Идемпотентно.
Запуск: PYTHONPATH=/app python /tmp/filltitles.py
"""
import asyncio
from sqlalchemy import select
from app.db import AsyncSessionLocal
from app.models import FinContent

TITLES = {
    "R1":  "Поддержка без стратегии",
    "R2":  "Стратегия опережает исполнение",
    "R3":  "Люди компенсируют системы",
    "R4":  "Системы без людей",
    "R5":  "Сильная команда в хаосе процессов",
    "R6":  "Трансформация в турбулентной среде",
    "R7":  "Стратегия без спонсора",
    "R8":  "Рутина без развития",
    "R9":  "Зависимость от воли спонсора",
    "R10": "Изменения без носителей",
    "R11": "Устаревшие системы в меняющейся среде",
    "R12": "Фазовый переход",
}


async def main():
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(FinContent).where(FinContent.kind == "tension_rule")
        )).scalars().all()
        updated = missing = 0
        found = set()
        for row in rows:
            title = TITLES.get(row.key)
            if title is None:
                continue
            found.add(row.key)
            row.payload = {**row.payload, "title": title}   # новый dict — JSONB увидит изменение
            updated += 1
            print(f"  {row.key}: {title}")
        for key in TITLES:
            if key not in found:
                print(f"  ! {key}: строки нет в БД"); missing += 1
        await session.commit()
        print(f"\nЗаголовков обновлено: {updated}, отсутствует правил: {missing}")

if __name__ == "__main__":
    asyncio.run(main())
