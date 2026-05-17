"""
Seed script: создаёт шаблоны всех 64 стратегий в БД.
Запуск: docker exec dao64_backend python seed_strategies.py
Уже существующие комбинации пропускаются (INSERT ... ON CONFLICT DO NOTHING).
"""
import asyncio
import uuid
from app.db import async_session_maker
from app.models import Strategy
from sqlalchemy import select

HEXAGRAMS = [
    ("AAAAAA", "Действие",              "Расцвет",     "AABAAA", "Развитие"),
    ("AAAAAB", "Реакция",               "Зарождение",  "BBBBAB", "Точность"),
    ("AAAABA", "Появление",             "Зарождение",  "BBAAAA", "Реформа"),
    ("AAAABB", "Формализация",          "Зарождение",  "AAABBA", "Управление"),
    ("AAABAA", "Бдительность",          "Расцвет",     "BBBBBA", "Завершение"),
    ("AAABAB", "Раздор",                "Упадок",      "AAABAB", "Раздор"),
    ("AAABBA", "Управление",            "Зарождение",  "BBBBAB", "Точность"),
    ("AAABBB", "Объединение",           "Зарождение",  "ABABBA", "Разрушение"),
    ("AABAAA", "Развитие",              "Расцвет",     "BAABAA", "Гармония"),
    ("AABAAB", "Последовательность",    "Расцвет",     "ABBAAA", "Естественность"),
    ("AABABA", "Достижение",            "Расцвет",     "BAAABB", "Неблагоприятный"),
    ("AABABB", "Препятствие",           "Упадок",      "AABAAA", "Развитие"),
    ("AABBAA", "Осознанность",          "Расцвет",     "BAABAA", "Гармония"),
    ("AABBAB", "Процветание",           "Расцвет",     "ABBAAB", "Изобилие"),
    ("AABBBA", "Смирение",              "Обновление",  "AABABA", "Достижение"),
    ("AABBBB", "Радость",               "Расцвет",     "BBABAB", "Амбиции"),
    ("ABAAAA", "Соответствие",          "Обновление",  "BBBBBA", "Завершение"),
    ("ABAAAB", "Диссонанс",             "Обновление",  "BBBBBB", "Незавершённость"),
    ("ABAABA", "Подход",                "Расцвет",     "BAAAAB", "Сила"),
    ("ABAABB", "Наблюдать",             "Обновление",  "BAAAAA", "Благоразумие"),
    ("ABABAA", "Устранять",             "Упадок",      "BBBBBB", "Незавершённость"),
    ("ABABAB", "Изящество",             "Расцвет",     "ABAAAB", "Диссонанс"),
    ("ABABBA", "Разрушение",            "Упадок",      "BBABBB", "Стимулирование"),
    ("ABABBB", "Возрождение",           "Зарождение",  "ABAABA", "Подход"),
    ("ABBAAA", "Естественность",        "Расцвет",     "BAABAA", "Гармония"),
    ("ABBAAB", "Изобилие",              "Обновление",  "ABABAB", "Изящество"),
    ("ABBABA", "Умеренность",           "Зарождение",  "AAAABB", "Формализация"),
    ("ABBABB", "Избыток",               "Обновление",  "BABABB", "Встреча"),
    ("ABBBAA", "Решимость",             "Упадок",      "AAAABA", "Появление"),
    ("ABBBAB", "Великолепие",           "Зрелость",    "ABABAB", "Изящество"),
    ("ABBBBA", "Влияние",               "Расцвет",     "BABABA", "Прорыв"),
    ("ABBBBB", "Выносливость",          "Зарождение",  "BABABB", "Встреча"),
    ("BAAAAA", "Благоразумие",          "Упадок",      "AAAAAA", "Действие"),
    ("BAAAAB", "Сила",                  "Расцвет",     "AAAAAA", "Действие"),
    ("BAAABA", "Благоприятный",         "Расцвет",     "BBBBBB", "Незавершённость"),
    ("BAAABB", "Неблагоприятный",       "Упадок",      "BAABAA", "Гармония"),
    ("BAABAA", "Гармония",              "Зарождение",  "BBBBBA", "Завершение"),
    ("BAABAB", "Полярность",            "Упадок",      "ABABAA", "Устранять"),
    ("BAABBA", "Трудность",             "Упадок",      "AAABAA", "Бдительность"),
    ("BAABBB", "Избавление",            "Обновление",  "BABBAB", "Самоотдача"),
    ("BABAAA", "Убыток",                "Упадок",      "ABBABA", "Умеренность"),
    ("BABAAB", "Прибыль",               "Расцвет",     "AAAABA", "Появление"),
    ("BABABA", "Прорыв",                "Расцвет",     "AAABAA", "Бдительность"),
    ("BABABB", "Встреча",               "Расцвет",     "BAAAAA", "Благоразумие"),
    ("BABBAA", "Объединение",           "Зарождение",  "BBBAAB", "Бодрость"),
    ("BABBAB", "Самоотдача",            "Расцвет",     "BBBAAA", "Интуиция"),
    ("BABBBA", "Понимание",             "Упадок",      "BABABB", "Встреча"),
    ("BABBBB", "Глубина",               "Обновление",  "BABBBA", "Понимание"),
    ("BBAAAA", "Реформа",               "Обновление",  "BBBBBA", "Завершение"),
    ("BBAAAB", "Ценности",              "Расцвет",     "ABAAAB", "Диссонанс"),
    ("BBAABA", "Смелость",              "Зарождение",  "ABBAAA", "Естественность"),
    ("BBAABB", "Сосредоточенность",     "Обновление",  "ABAAAB", "Диссонанс"),
    ("BBABAA", "Готовность",            "Обновление",  "BAABBA", "Трудность"),
    ("BBABAB", "Амбиции",               "Упадок",      "AABABA", "Достижение"),
    ("BBABBA", "Изобилие",              "Расцвет",     "BAAABB", "Неблагоприятный"),
    ("BBABBB", "Стимулирование",        "Упадок",      "AABBAB", "Процветание"),
    ("BBBAAA", "Интуиция",              "Обновление",  "BABABB", "Встреча"),
    ("BBBAAB", "Бодрость",              "Расцвет",     "AAABAA", "Бдительность"),
    ("BBBABA", "Установление связей",   "Обновление",  "BABABB", "Встреча"),
    ("BBBABB", "Реализм",               "Обновление",  "BABABA", "Прорыв"),
    ("BBBBAA", "Внутренняя правда",     "Расцвет",     "BABAAB", "Прибыль"),
    ("BBBBAB", "Точность",              "Упадок",      "BAAAAA", "Благоразумие"),
    ("BBBBBA", "Завершение",            "Зрелость",    "ABAAAA", "Соответствие"),
    ("BBBBBB", "Незавершённость",       "Зарождение",  "BAABBB", "Избавление"),
]


async def main():
    async with async_session_maker() as session:
        created = 0
        skipped = 0
        for combo, name, stage, target_combo, target_name in HEXAGRAMS:
            existing = await session.scalar(
                select(Strategy).where(Strategy.combination == combo)
            )
            if existing:
                skipped += 1
                continue

            s = Strategy(
                id=uuid.uuid4(),
                combination=combo,
                title=name,
                lifecycle_stage=stage,
                transition_title=target_name,
                current_state={"combination": combo, "hex_name": name},
                is_published=False,
            )
            session.add(s)
            created += 1

        await session.commit()
        print(f"✓ Создано: {created}, пропущено (уже есть): {skipped}")


if __name__ == "__main__":
    asyncio.run(main())
