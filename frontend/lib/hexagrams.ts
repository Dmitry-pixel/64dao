// Единый источник истины для гексаграмм (номер, комбинация, название, стадия).
// Потребители: admin/strategies/[combination], report/[id], AdminNav.
// Имена гексаграмм меняем ТОЛЬКО здесь.
export type Hexagram = { n: number; combo: string; name: string; stage: string };

export const HEXAGRAM_DATA: Hexagram[] = [
  { n:  1, combo: 'AAAAAA', name: 'Действие',            stage: 'Расцвет'    },
  { n:  2, combo: 'BBBBBB', name: 'Реакция',             stage: 'Зарождение' },
  { n:  3, combo: 'ABBBAB', name: 'Появление',           stage: 'Зарождение' },
  { n:  4, combo: 'BABBBA', name: 'Формализация',        stage: 'Зарождение' },
  { n:  5, combo: 'AAABAB', name: 'Бдительность',        stage: 'Расцвет'    },
  { n:  6, combo: 'BABAAA', name: 'Раздор',              stage: 'Упадок'     },
  { n:  7, combo: 'BABBBB', name: 'Управление',          stage: 'Зарождение' },
  { n:  8, combo: 'BBBBAB', name: 'Сближение',           stage: 'Зарождение' },
  { n:  9, combo: 'AAABAA', name: 'Развитие',            stage: 'Расцвет'    },
  { n: 10, combo: 'AABAAA', name: 'Последовательность',  stage: 'Расцвет'    },
  { n: 11, combo: 'AAABBB', name: 'Достижение',          stage: 'Расцвет'    },
  { n: 12, combo: 'BBBAAA', name: 'Препятствие',         stage: 'Упадок'     },
  { n: 13, combo: 'ABAAAA', name: 'Осознанность',        stage: 'Расцвет'    },
  { n: 14, combo: 'AAAABA', name: 'Процветание',         stage: 'Расцвет'    },
  { n: 15, combo: 'BBABBB', name: 'Смирение',            stage: 'Обновление' },
  { n: 16, combo: 'BBBABB', name: 'Радость',             stage: 'Расцвет'    },
  { n: 17, combo: 'ABBAAB', name: 'Соответствие',        stage: 'Обновление' },
  { n: 18, combo: 'BAABBA', name: 'Диссонанс',           stage: 'Обновление' },
  { n: 19, combo: 'AABBBB', name: 'Подход',              stage: 'Расцвет'    },
  { n: 20, combo: 'BBBBAA', name: 'Наблюдать',           stage: 'Обновление' },
  { n: 21, combo: 'ABBABA', name: 'Устранять',           stage: 'Упадок'     },
  { n: 22, combo: 'ABABBA', name: 'Изящество',           stage: 'Расцвет'    },
  { n: 23, combo: 'BBBBBA', name: 'Разрушение',          stage: 'Упадок'     },
  { n: 24, combo: 'ABBBBB', name: 'Возрождение',         stage: 'Зарождение' },
  { n: 25, combo: 'ABBAAA', name: 'Естественность',      stage: 'Расцвет'    },
  { n: 26, combo: 'AAABBA', name: 'Накопление',          stage: 'Обновление' },
  { n: 27, combo: 'ABBBBA', name: 'Умеренность',         stage: 'Зарождение' },
  { n: 28, combo: 'BAAAAB', name: 'Избыток',             stage: 'Обновление' },
  { n: 29, combo: 'BABBAB', name: 'Решимость',           stage: 'Упадок'     },
  { n: 30, combo: 'ABAABA', name: 'Великолепие',         stage: 'Зрелость'   },
  { n: 31, combo: 'BBAAAB', name: 'Влияние',             stage: 'Расцвет'    },
  { n: 32, combo: 'BAAABB', name: 'Выносливость',        stage: 'Зарождение' },
  { n: 33, combo: 'BBAAAA', name: 'Благоразумие',        stage: 'Упадок'     },
  { n: 34, combo: 'AAAABB', name: 'Сила',                stage: 'Расцвет'    },
  { n: 35, combo: 'BBBABA', name: 'Благоприятный',       stage: 'Расцвет'    },
  { n: 36, combo: 'ABABBB', name: 'Неблагоприятный',     stage: 'Упадок'     },
  { n: 37, combo: 'ABABAA', name: 'Гармония',            stage: 'Зарождение' },
  { n: 38, combo: 'AABABA', name: 'Полярность',          stage: 'Упадок'     },
  { n: 39, combo: 'BBABAB', name: 'Трудность',           stage: 'Упадок'     },
  { n: 40, combo: 'BABABB', name: 'Избавление',          stage: 'Обновление' },
  { n: 41, combo: 'AABBBA', name: 'Убыток',              stage: 'Упадок'     },
  { n: 42, combo: 'ABBBAA', name: 'Прибыль',             stage: 'Расцвет'    },
  { n: 43, combo: 'AAAAAB', name: 'Прорыв',              stage: 'Расцвет'    },
  { n: 44, combo: 'BAAAAA', name: 'Встреча',             stage: 'Расцвет'    },
  { n: 45, combo: 'BBBAAB', name: 'Объединение',         stage: 'Зарождение' },
  { n: 46, combo: 'BAABBB', name: 'Самоотдача',          stage: 'Расцвет'    },
  { n: 47, combo: 'BABAAB', name: 'Понимание',           stage: 'Упадок'     },
  { n: 48, combo: 'BAABAB', name: 'Глубина',             stage: 'Обновление' },
  { n: 49, combo: 'ABAAAB', name: 'Реформа',             stage: 'Обновление' },
  { n: 50, combo: 'BAAABA', name: 'Ценности',            stage: 'Расцвет'    },
  { n: 51, combo: 'ABBABB', name: 'Смелость',            stage: 'Зарождение' },
  { n: 52, combo: 'BBABBA', name: 'Сосредоточенность',   stage: 'Обновление' },
  { n: 53, combo: 'BBABAA', name: 'Готовность',          stage: 'Обновление' },
  { n: 54, combo: 'AABABB', name: 'Амбиции',             stage: 'Упадок'     },
  { n: 55, combo: 'ABAABB', name: 'Изобилие',            stage: 'Расцвет'    },
  { n: 56, combo: 'BBAABA', name: 'Стимулирование',      stage: 'Упадок'     },
  { n: 57, combo: 'BABBAA', name: 'Интуиция',            stage: 'Обновление' },
  { n: 58, combo: 'AABAAB', name: 'Бодрость',            stage: 'Расцвет'    },
  { n: 59, combo: 'BAABAA', name: 'Установление связей', stage: 'Обновление' },
  { n: 60, combo: 'AABBAB', name: 'Реализм',             stage: 'Обновление' },
  { n: 61, combo: 'AABBAA', name: 'Внутренняя правда',   stage: 'Расцвет'    },
  { n: 62, combo: 'BBAABB', name: 'Точность',            stage: 'Упадок'     },
  { n: 63, combo: 'ABABAB', name: 'Завершение',          stage: 'Зрелость'   },
  { n: 64, combo: 'BABABA', name: 'Незавершённость',     stage: 'Зарождение' },
];

export const HEXAGRAM_MAP: Record<string, Hexagram> = {};
for (const h of HEXAGRAM_DATA) HEXAGRAM_MAP[h.combo] = h;

export const HEX_TUPLE: Record<string, [number, string]> = {};
for (const h of HEXAGRAM_DATA) HEX_TUPLE[h.combo] = [h.n, h.name];

export function comboToHex(combo: string): string {
  const e = HEXAGRAM_MAP[combo];
  return e ? String.fromCodePoint(0x4DC0 + e.n - 1) : '?';
}
