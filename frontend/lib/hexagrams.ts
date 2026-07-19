// Единый источник истины для гексаграмм (номер, комбинация, название, стадия).
// Потребители: admin/strategies/[combination], report/[id], AdminNav.
// Имена гексаграмм меняем ТОЛЬКО здесь.
export type Hexagram = { n: number; combo: string; name: string };

export const HEXAGRAM_DATA: Hexagram[] = [
  { n:  1, combo: 'AAAAAA', name: 'Действие' },
  { n:  2, combo: 'BBBBBB', name: 'Реакция' },
  { n:  3, combo: 'ABBBAB', name: 'Появление' },
  { n:  4, combo: 'BABBBA', name: 'Формализация' },
  { n:  5, combo: 'AAABAB', name: 'Бдительность' },
  { n:  6, combo: 'BABAAA', name: 'Раздор' },
  { n:  7, combo: 'BABBBB', name: 'Управление' },
  { n:  8, combo: 'BBBBAB', name: 'Сближение' },
  { n:  9, combo: 'AAABAA', name: 'Развитие' },
  { n: 10, combo: 'AABAAA', name: 'Последовательность' },
  { n: 11, combo: 'AAABBB', name: 'Достижение' },
  { n: 12, combo: 'BBBAAA', name: 'Препятствие' },
  { n: 13, combo: 'ABAAAA', name: 'Осознанность' },
  { n: 14, combo: 'AAAABA', name: 'Процветание' },
  { n: 15, combo: 'BBABBB', name: 'Смирение' },
  { n: 16, combo: 'BBBABB', name: 'Радость' },
  { n: 17, combo: 'ABBAAB', name: 'Соответствие' },
  { n: 18, combo: 'BAABBA', name: 'Диссонанс' },
  { n: 19, combo: 'AABBBB', name: 'Подход' },
  { n: 20, combo: 'BBBBAA', name: 'Наблюдать' },
  { n: 21, combo: 'ABBABA', name: 'Устранять' },
  { n: 22, combo: 'ABABBA', name: 'Изящество' },
  { n: 23, combo: 'BBBBBA', name: 'Разрушение' },
  { n: 24, combo: 'ABBBBB', name: 'Возрождение' },
  { n: 25, combo: 'ABBAAA', name: 'Естественность' },
  { n: 26, combo: 'AAABBA', name: 'Накопление' },
  { n: 27, combo: 'ABBBBA', name: 'Умеренность' },
  { n: 28, combo: 'BAAAAB', name: 'Избыток' },
  { n: 29, combo: 'BABBAB', name: 'Решимость' },
  { n: 30, combo: 'ABAABA', name: 'Великолепие' },
  { n: 31, combo: 'BBAAAB', name: 'Влияние' },
  { n: 32, combo: 'BAAABB', name: 'Выносливость' },
  { n: 33, combo: 'BBAAAA', name: 'Благоразумие' },
  { n: 34, combo: 'AAAABB', name: 'Сила' },
  { n: 35, combo: 'BBBABA', name: 'Благоприятный' },
  { n: 36, combo: 'ABABBB', name: 'Неблагоприятный' },
  { n: 37, combo: 'ABABAA', name: 'Гармония' },
  { n: 38, combo: 'AABABA', name: 'Полярность' },
  { n: 39, combo: 'BBABAB', name: 'Трудность' },
  { n: 40, combo: 'BABABB', name: 'Избавление' },
  { n: 41, combo: 'AABBBA', name: 'Убыток' },
  { n: 42, combo: 'ABBBAA', name: 'Прибыль' },
  { n: 43, combo: 'AAAAAB', name: 'Прорыв' },
  { n: 44, combo: 'BAAAAA', name: 'Встреча' },
  { n: 45, combo: 'BBBAAB', name: 'Объединение' },
  { n: 46, combo: 'BAABBB', name: 'Самоотдача' },
  { n: 47, combo: 'BABAAB', name: 'Понимание' },
  { n: 48, combo: 'BAABAB', name: 'Глубина' },
  { n: 49, combo: 'ABAAAB', name: 'Реформа' },
  { n: 50, combo: 'BAAABA', name: 'Ценности' },
  { n: 51, combo: 'ABBABB', name: 'Смелость' },
  { n: 52, combo: 'BBABBA', name: 'Сосредоточенность' },
  { n: 53, combo: 'BBABAA', name: 'Готовность' },
  { n: 54, combo: 'AABABB', name: 'Амбиции' },
  { n: 55, combo: 'ABAABB', name: 'Изобилие' },
  { n: 56, combo: 'BBAABA', name: 'Стимулирование' },
  { n: 57, combo: 'BAABAA', name: 'Интуиция' },
  { n: 58, combo: 'AABAAB', name: 'Бодрость' },
  { n: 59, combo: 'BABBAA', name: 'Установление связей' },
  { n: 60, combo: 'AABBAB', name: 'Реализм' },
  { n: 61, combo: 'AABBAA', name: 'Внутренняя правда' },
  { n: 62, combo: 'BBAABB', name: 'Точность' },
  { n: 63, combo: 'ABABAB', name: 'Завершение' },
  { n: 64, combo: 'BABABA', name: 'Незавершённость' },
];

export const HEXAGRAM_MAP: Record<string, Hexagram> = {};
for (const h of HEXAGRAM_DATA) HEXAGRAM_MAP[h.combo] = h;

export const HEX_TUPLE: Record<string, [number, string]> = {};
for (const h of HEXAGRAM_DATA) HEX_TUPLE[h.combo] = [h.n, h.name];

export function comboToHex(combo: string): string {
  const e = HEXAGRAM_MAP[combo];
  return e ? String.fromCodePoint(0x4DC0 + e.n - 1) : '?';
}
