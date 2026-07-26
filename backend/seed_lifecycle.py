"""
Скрипт заполнения lifecycle_description и 6 lc_* полей для всех 64 стратегий.

Запуск:
  docker exec dao64_backend python seed_lifecycle.py
"""

import asyncio
from sqlalchemy import select
from app.db import AsyncSessionLocal as async_session_maker
from app.models import Strategy

# Формулировки и подписи берутся из единого источника — app/method1_questions.
# Локальных копий здесь быть не должно (см. tests/test_base_questions_mapping.py).
from app.method1_questions import ANSWERS, LC_FIELDS, QUESTION_LABELS  # noqa: E402


def generate_description(combination: str) -> str:
    lines = []
    for i, letter in enumerate(combination):
        label = QUESTION_LABELS[i]
        answer = ANSWERS[i][0] if letter == "A" else ANSWERS[i][1]
        lines.append(f"{i + 1}. {label} – {answer}.")
    return "\n".join(lines)


async def main():
    async with async_session_maker() as session:
        result = await session.execute(select(Strategy))
        strategies = result.scalars().all()

        updated = 0
        for s in strategies:
            if not s.combination or len(s.combination) != 6:
                continue

            # lifecycle_description — сводный текст для совместимости
            if not (s.lifecycle_description or "").strip():
                s.lifecycle_description = generate_description(s.combination)

            # 6 полей профиля — только первичное заполнение пустых.
            # Это редактируемый контент карточки стратагемы: безусловная
            # перезапись затирала бы авторские правки при каждом прогоне.
            for i, field in enumerate(LC_FIELDS):
                if not (getattr(s, field, None) or "").strip():
                    setattr(s, field, ANSWERS[i][0] if s.combination[i] == "A" else ANSWERS[i][1])

            updated += 1

        await session.commit()
        print(f"Обновлено {updated} из {len(strategies)} стратегий.")


if __name__ == "__main__":
    asyncio.run(main())
