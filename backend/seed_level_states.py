"""
Seed (идемпотентный): 12 состояний уровней (сань-цай) в fin_content.

Значения по умолчанию берутся из app/level_state_texts — единого источника.
После заливки тексты правятся в админке (/admin/fin-content) и код их больше
не перетирает: повторный запуск синхронизирует только структурные поля (title)
и не трогает отредактированные формулировки.

Запуск: docker compose exec backend python seed_level_states.py
Полный сброс к значениям из кода: добавить аргумент --reset
"""
import asyncio
import sys
import uuid

from sqlalchemy import select

from app.db import AsyncSessionLocal as async_session_maker
from app.level_state_texts import KEYS, KIND, STRUCTURAL_FIELDS, default_payload
from app.models import FinContent


async def main(reset: bool = False):
    async with async_session_maker() as session:
        inserted = updated = kept = 0
        for i, key in enumerate(KEYS):
            payload = default_payload(key)
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
        print(f"level_state: вставлено {inserted}, сброшено {updated}, "
              f"сохранено с правками {kept}")


if __name__ == "__main__":
    asyncio.run(main(reset="--reset" in sys.argv))
