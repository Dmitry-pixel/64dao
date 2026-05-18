"""
Скрипт заполнения lifecycle_description для всех 64 стратегий.

Запуск:
  docker exec dao64_backend python seed_lifecycle.py
"""

import asyncio
from sqlalchemy import select, update
from app.db import AsyncSessionLocal as async_session_maker
from app.models import Strategy

# Описания для каждой позиции (A/B) и каждого из 6 вопросов
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
        "Первопроходец (создание новых решений и рынков). Создаёт новые категории, продукты или подходы",
        "Быстрый последователь (адаптация уже подтверждённых решений). Быстро адаптирует и улучшает существующие решения",
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


def generate_description(combination: str) -> str:
    """Генерирует текст lifecycle_description из 6-буквенной комбинации."""
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
            text = generate_description(s.combination)
            s.lifecycle_description = text
            updated += 1

        await session.commit()
        print(f"Обновлено {updated} из {len(strategies)} стратегий.")


if __name__ == "__main__":
    asyncio.run(main())
