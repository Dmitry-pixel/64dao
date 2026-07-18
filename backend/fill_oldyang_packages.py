# -*- coding: utf-8 -*-
"""
Пакеты действий для подвижных Ян-линий (старый Ян) — Спецификация §5.6:
предупреждения об удержании. ЧЕРНОВИКИ — правка через админку (fin-content).
Идемпотентно: upsert по (kind, key). Запуск: PYTHONPATH=/app python /tmp/fillold.py
"""
import asyncio, uuid
from sqlalchemy import select
from app.db import AsyncSessionLocal
from app.models import FinContent

ROWS = [
    ("line1_oldyang", "1. Процессы",
     "Процессы на пике зрелости: держите регламенты живыми — без регулярного пересмотра они костенеют и отстают от бизнеса. Риск деградации: изменение структуры бизнеса без обновления процессов."),
    ("line2_oldyang", "2. Системы",
     "Системы сильны: контролируйте архитектуру и качество данных — без развития платформа устаревает незаметно. Риск деградации: рост объёмов и новые контуры учёта без плана масштабирования."),
    ("line3_oldyang", "3. Команда",
     "Команда на пике: удерживайте носителей ключевых компетенций и планируйте преемственность — сила персональна и уязвима к уходу людей. Риск деградации: выгорание и отсутствие развития."),
    ("line4_oldyang", "4. Руководство",
     "Поддержка руководства на максимуме: институционализируйте её — управляющий комитет, регулярный ритм, закреплённые полномочия. Риск деградации: смена первого лица или его приоритетов."),
    ("line5_oldyang", "5. Среда",
     "Среда стабильна: используйте окно для укрепления фундамента — стабильность внешних условий не бывает вечной. Риск деградации: регуляторные изменения и структурные сдвиги бизнеса."),
    ("line6_oldyang", "6. Стратегия",
     "Стратегия ясна и принята: поддерживайте её актуальность и коммуникацию — сильное видение устаревает тихо. Риск деградации: расхождение целей функции с обновлённой стратегией компании."),
]


async def main():
    async with AsyncSessionLocal() as session:
        ins = upd = 0
        for i, (key, title, text) in enumerate(ROWS):
            row = await session.scalar(select(FinContent).where(
                FinContent.kind == "action_package", FinContent.key == key))
            payload = {"title": title, "text": text}
            if row is None:
                session.add(FinContent(id=uuid.uuid4(), kind="action_package",
                                       key=key, payload=payload, sort=10 + i))
                ins += 1
            else:
                row.payload = payload; row.sort = 10 + i; upd += 1
        await session.commit()
        print(f"action_package (старый Ян): вставлено {ins}, обновлено {upd}")

if __name__ == "__main__":
    asyncio.run(main())
