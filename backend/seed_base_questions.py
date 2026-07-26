"""
Seed (идемпотентный): 6 базовых вопросов Метода 1 в fin_content.

Значения по умолчанию берутся из app/method1_questions — единого источника.
После заливки тексты правятся в админке (/admin/fin-content, вид «Базовые
вопросы») и код их больше не перетирает: повторный запуск обновляет только
структурные поля (lc_key, label) и не трогает отредактированные формулировки.

Запуск: docker compose exec backend python seed_base_questions.py
Полный сброс к значениям из кода: добавить аргумент --reset
"""
import asyncio
import sys
import uuid

from sqlalchemy import select

from app.base_questions import KEYS, KIND, STRUCTURAL_FIELDS, default_payload
from app.db import AsyncSessionLocal as async_session_maker
from app.models import FinContent


async def main(reset: bool = False):
    async with async_session_maker() as session:
        inserted = updated = kept = 0
        for i, key in enumerate(KEYS):
            payload = default_payload(i)
            row = (await session.execute(
                select(FinContent).where(
                    FinContent.kind == KIND,
                    FinContent.key == key,
                    FinContent.contour == "common",
                )
            )).scalar_one_or_none()

            if row is None:
                session.add(FinContent(
                    id=uuid.uuid4(), kind=KIND, key=key, contour="common",
                    payload=payload, sort=i,
                ))
                inserted += 1
            elif reset:
                row.payload = payload
                row.sort = i
                updated += 1
            else:
                # Формулировки могли быть отредактированы — сохраняем их,
                # синхронизируем только структурные поля.
                merged = dict(row.payload or {})
                for f in STRUCTURAL_FIELDS:
                    merged[f] = payload[f]
                for f, v in payload.items():
                    merged.setdefault(f, v)
                row.payload = merged
                row.sort = i
                kept += 1
        await session.commit()
        print(f"base_questions: вставлено {inserted}, сброшено {updated}, "
              f"сохранено с правками {kept}")


if __name__ == "__main__":
    asyncio.run(main(reset="--reset" in sys.argv))
