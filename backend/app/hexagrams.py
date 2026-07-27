# -*- coding: utf-8 -*-
# Единый источник истины для гексаграмм: (номер, название, комбинация).
# Потребитель: pdf.py. Имена гексаграмм меняем ТОЛЬКО здесь.

HEXAGRAM_LIST: list[tuple[int, str, str]] = [
    (1,  "Действие",              "AAAAAA"),
    (2,  "Реакция",               "BBBBBB"),
    (3,  "Появление",             "ABBBAB"),
    (4,  "Формализация",          "BABBBA"),
    (5,  "Бдительность",          "AAABAB"),
    (6,  "Раздор",                "BABAAA"),
    (7,  "Управление",            "BABBBB"),
    (8,  "Сближение",             "BBBBAB"),
    (9,  "Развитие",              "AAABAA"),
    (10, "Последовательность",    "AABAAA"),
    (11, "Достижение",            "AAABBB"),
    (12, "Препятствие",           "BBBAAA"),
    (13, "Осознанность",          "ABAAAA"),
    (14, "Процветание",           "AAAABA"),
    (15, "Смирение",              "BBABBB"),
    (16, "Радость",               "BBBABB"),
    (17, "Соответствие",          "ABBAAB"),
    (18, "Диссонанс",             "BAABBA"),
    (19, "Подход",                "AABBBB"),
    (20, "Наблюдать",             "BBBBAA"),
    (21, "Устранять",             "ABBABA"),
    (22, "Изящество",             "ABABBA"),
    (23, "Разрушение",            "BBBBBA"),
    (24, "Возрождение",           "ABBBBB"),
    (25, "Естественность",        "ABBAAA"),
    (26, "Накопление",            "AAABBA"),
    (27, "Умеренность",           "ABBBBA"),
    (28, "Избыток",               "BAAAAB"),
    (29, "Решимость",             "BABBAB"),
    (30, "Великолепие",           "ABAABA"),
    (31, "Влияние",               "BBAAAB"),
    (32, "Выносливость",          "BAAABB"),
    (33, "Благоразумие",          "BBAAAA"),
    (34, "Сила",                  "AAAABB"),
    (35, "Благоприятный",         "BBBABA"),
    (36, "Неблагоприятный",       "ABABBB"),
    (37, "Гармония",              "ABABAA"),
    (38, "Полярность",            "AABABA"),
    (39, "Трудность",             "BBABAB"),
    (40, "Избавление",            "BABABB"),
    (41, "Убыток",                "AABBBA"),
    (42, "Прибыль",               "ABBBAA"),
    (43, "Прорыв",                "AAAAAB"),
    (44, "Встреча",               "BAAAAA"),
    (45, "Объединение",           "BBBAAB"),
    (46, "Самоотдача",            "BAABBB"),
    (47, "Понимание",             "BABAAB"),
    (48, "Глубина",               "BAABAB"),
    (49, "Реформа",               "ABAAAB"),
    (50, "Ценности",              "BAAABA"),
    (51, "Смелость",              "ABBABB"),
    (52, "Сосредоточенность",     "BBABBA"),
    (53, "Готовность",            "BBABAA"),
    (54, "Амбиции",               "AABABB"),
    (55, "Изобилие",              "ABAABB"),
    (56, "Стимулирование",        "BBAABA"),
    (57, "Интуиция",              "BAABAA"),
    (58, "Бодрость",              "AABAAB"),
    (59, "Установление связей",   "BABBAA"),
    (60, "Реализм",               "AABBAB"),
    (61, "Внутренняя правда",     "AABBAA"),
    (62, "Точность",              "BBAABB"),
    (63, "Завершение",            "ABABAB"),
    (64, "Незавершённость",       "BABABA"),
]


_HEXAGRAM_LIST = HEXAGRAM_LIST

# combination → (number, name)
_HEXAGRAM_BY_COMBO: dict[str, tuple[int, str]] = {
    combo: (num, name) for num, name, combo in _HEXAGRAM_LIST
}

# number → name
_HEXAGRAM_BY_NUM: dict[int, str] = {
    num: name for num, name, _ in _HEXAGRAM_LIST
}

# number → combination
_COMBO_BY_NUM: dict[int, str] = {num: combo for num, name, combo in _HEXAGRAM_LIST}

# Таблица соответствия: номер текущей гексаграммы → номер целевой
_TARGET_HEXAGRAM: dict[int, int] = {
     1:  9,  2: 62,  3: 49,  4:  7,  5: 63,  6:  6,  7: 62,  8: 23,
     9: 37, 10: 25, 11: 36, 12:  9, 13: 37, 14: 26, 15: 11, 16: 54,
    17: 63, 18: 64, 19: 34, 20: 33, 21: 64, 22: 18, 23: 56, 24: 19,
    25: 37, 26: 22, 27:  4, 28: 44, 29:  3, 30: 22, 31: 43, 32: 44,
    33:  1, 34:  1, 35: 64, 36: 37, 37: 63, 38: 21, 39:  5, 40: 46,
    41: 27, 42:  3, 43:  5, 44: 33, 45: 58, 46: 57, 47: 44, 48: 47,
    49: 63, 50: 18, 51: 25, 52: 18, 53: 39, 54: 11, 55: 36, 56: 14,
    57: 44, 58:  5, 59: 44, 60: 43, 61: 42, 62: 33, 63: 17, 64: 40,
}


def get_target_hexagram_info(combination: str) -> tuple[int, str, str] | None:
    """
    По комбинации (напр. ABABBA) возвращает (номер, название, символ)
    целевой гексаграммы. Символ — Unicode U+4DC0 + num - 1.
    Возвращает None, если комбинация не найдена.
    """
    entry = _HEXAGRAM_BY_COMBO.get(combination)
    if not entry:
        return None
    current_num, _ = entry
    target_num = _TARGET_HEXAGRAM.get(current_num)
    if not target_num:
        return None
    target_name = _HEXAGRAM_BY_NUM.get(target_num, "")
    target_symbol = chr(0x4DC0 + target_num - 1)
    return target_num, target_name, target_symbol


def hexagram_symbol(num: int | None) -> str:
    """Unicode-символ гексаграммы по номеру: U+4DC0 + num - 1."""
    return chr(0x4DC0 + num - 1) if num else ''
