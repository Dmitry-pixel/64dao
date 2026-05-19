"""
Скрипт заполнения lifecycle_description и 6 lc_* полей для всех 64 стратегий.

Запуск:
  docker exec dao64_backend python seed_lifecycle.py
"""

import asyncio
from sqlalchemy import select
from app.db import AsyncSessionLocal as async_session_maker
from app.models import Strategy

QUESTION_LABELS = [
    "Формирование прибыли",
    "Рыночная стратегия",
    "Принятие решений",
    "Тип потребителя",
    "Статус рынка",
    "Тип ценности",
]

ANSWERS = [
    # Вопрос 1: ЦЕЛЬ
    (
        "Рост выручки и объёма продаж",
        "Повышение эффективности, сокращение расходов и потерь",
    ),
    # Вопрос 2: СТРАТЕГИЯ
    (
        "Первопроходец — создание новых решений и рынков, новых категорий, продуктов или подходов",
        "Быстрый последователь — адаптация уже подтверждённых решений, быстрое улучшение существующего",
    ),
    # Вопрос 3: ОРГАНИЗАЦИЯ
    (
        "Преимущественно централизованно",
        "Преимущественно распределённо",
    ),
    # Вопрос 4: ТИП ПОТРЕБИТЕЛЯ
    (
        "Корпоративные клиенты (B2B)",
        "Частные потребители (B2C)",
    ),
    # Вопрос 5: СТАТУС РЫНКА
    (
        "Зрелый рынок с высокой конкуренцией",
        "Развивающийся рынок с формирующимся спросом",
    ),
    # Вопрос 6: ТИП ЦЕННОСТИ
    (
        "Технологические инновации",
        "Улучшение существующих решений",
    ),
]

LC_FIELDS = ['lc_profit', 'lc_strategy', 'lc_decisions', 'lc_consumer', 'lc_market', 'lc_value']


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
            s.lifecycle_description = generate_description(s.combination)

            # 6 отдельных lc_* полей — заполняем всегда (авто-заполнение из комбинации)
            for i, field in enumerate(LC_FIELDS):
                setattr(s, field, ANSWERS[i][0] if s.combination[i] == "A" else ANSWERS[i][1])

            updated += 1

        await session.commit()
        print(f"Обновлено {updated} из {len(strategies)} стратегий.")


if __name__ == "__main__":
    asyncio.run(main())
