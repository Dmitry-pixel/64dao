'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

// A=Yang (сплошная), B=Yin (прерывистая). offset = parseInt(combo, 2) где A→0, B→1
function comboToHex(combo: string): string {
  const entry = HEXAGRAM_DATA.find(h => h.combo === combo);
  if (!entry) return '?';
  return String.fromCodePoint(0x4DC0 + entry.n - 1);
}

// Данные из документа пользователя (с исправлениями дубликатов)
const HEXAGRAM_DATA = [
  { n:  1, combo: 'AAAAAA', name: 'Действие',            stage: 'Расцвет'    },
  { n:  2, combo: 'BBBBBB', name: 'Реакция',             stage: 'Зарождение' },
  { n:  3, combo: 'ABBBAB', name: 'Появление',           stage: 'Зарождение' },
  { n:  4, combo: 'BABBBA', name: 'Формализация',        stage: 'Зарождение' },
  { n:  5, combo: 'AAABAB', name: 'Бдительность',        stage: 'Расцвет'    },
  { n:  6, combo: 'BABAAA', name: 'Раздор',              stage: 'Упадок'     },
  { n:  7, combo: 'BABBBB', name: 'Управление',          stage: 'Зарождение' },
  { n:  8, combo: 'BBBBAB', name: 'Объединение',         stage: 'Зарождение' },
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
  { n: 26, combo: 'AAABBA', name: 'Изобилие',            stage: 'Обновление' },
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
const HEXAGRAM_MAP: Record<string, typeof HEXAGRAM_DATA[0]> = {};
HEXAGRAM_DATA.forEach(h => { HEXAGRAM_MAP[h.combo] = h; });

// Таблица соответствия: номер текущей гексаграммы → номер целевой
const TARGET_HEXAGRAM: Record<number, number> = {
   1:  9,  2: 62,  3: 49,  4:  7,  5: 63,  6:  6,  7: 62,  8: 23,
   9: 37, 10: 25, 11: 36, 12:  9, 13: 37, 14: 26, 15: 11, 16: 54,
  17: 63, 18: 64, 19: 34, 20: 33, 21: 64, 22: 18, 23: 56, 24: 19,
  25: 37, 26: 22, 27:  4, 28: 44, 29:  3, 30: 22, 31: 43, 32: 44,
  33:  1, 34:  1, 35: 64, 36: 37, 37: 63, 38: 21, 39:  5, 40: 46,
  41: 27, 42:  3, 43:  5, 44: 33, 45: 58, 46: 57, 47: 44, 48: 47,
  49: 63, 50: 18, 51: 25, 52: 18, 53: 39, 54: 11, 55: 36, 56: 14,
  57: 44, 58:  5, 59: 44, 60: 43, 61: 42, 62: 33, 63: 17, 64: 40,
};

// Авто-заполнение 6 блоков жизненного цикла из комбинации
const LC_BLOCKS = [
  { key: 'lc_profit',    label: 'Формирование прибыли',
    a: 'Рост выручки и объёма продаж',
    b: 'Повышение эффективности, сокращение расходов и потерь' },
  { key: 'lc_strategy',  label: 'Рыночная стратегия',
    a: 'Первопроходец — создание новых решений и рынков, новых категорий, продуктов или подходов',
    b: 'Быстрый последователь — адаптация уже подтверждённых решений, быстрое улучшение существующего' },
  { key: 'lc_decisions', label: 'Принятие решений',
    a: 'Преимущественно централизованно',
    b: 'Преимущественно распределённо' },
  { key: 'lc_consumer',  label: 'Тип потребителя',
    a: 'Корпоративные клиенты (B2B)',
    b: 'Частные потребители (B2C)' },
  { key: 'lc_market',    label: 'Статус рынка',
    a: 'Зрелый рынок с высокой конкуренцией',
    b: 'Развивающийся рынок с формирующимся спросом' },
  { key: 'lc_value',     label: 'Тип ценности',
    a: 'Технологические инновации',
    b: 'Улучшение существующих решений' },
];

function autoFillLc(combination: string): Record<string, string> {
  const result: Record<string, string> = {};
  LC_BLOCKS.forEach((b, i) => {
    result[b.key] = combination[i] === 'A' ? b.a : b.b;
  });
  return result;
}

function getTargetHex(combo: string) {
  const cur = HEXAGRAM_MAP[combo];
  if (!cur) return null;
  const targetN = TARGET_HEXAGRAM[cur.n];
  if (!targetN) return null;
  return HEXAGRAM_DATA.find(h => h.n === targetN) || null;
}

// Поля точно соответствуют модели Strategy в БД
const EMPTY = {
  title: '',
  stratagema_title: '',
  lifecycle_stage: '',
  lifecycle_description: '',
  lc_profit: '',
  lc_strategy: '',
  lc_decisions: '',
  lc_consumer: '',
  lc_market: '',
  lc_value: '',
  scenario_text: '',
  marketing_text: '',
  management_text: '',
  // Предположения для связи с будущим
  assm_planning: '',
  assm_growth: '',
  assm_advertising: '',
  assm_feedback: '',
  assm_risk: '',
  assm_product: '',
  assm_service: '',
  assm_startup: '',
  assm_investment: '',
  assm_contracts: '',
  assm_sync: '',
  assm_creative: '',
  assm_interaction: '',
  transition_title: '',
  transition_lifecycle_stage: '',
  transition_description: '',
  is_published: false,
  // JSONB поля (редактируем как текст, сохраняем как объект)
  scenario_innovation_strategy: '',
  scenario_innovation_type: '',
  scenario_value_discipline: '',
  scenario_leadership_principles: '',
  scenario_growth_strategy: '',
  scenario_focus: '',
};

type Params = { params: { combination: string } };

export default function StrategyEditorPage({ params }: Params) {
  const router = useRouter();
  const { combination } = params;
  const hex = HEXAGRAM_MAP[combination];
  const [form, setForm] = useState({ ...EMPTY });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!hex) { setLoading(false); return; }
    // Pre-fill из статических данных + авто-заполнение lc_ из комбинации
    setForm(f => ({
      ...f,
      title: hex.name,
      lifecycle_stage: hex.stage,
      ...autoFillLc(combination),
    }));
    fetch(`/api/admin/strategies/combo/${combination}`, { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data || data.detail) return;
        // Разворачиваем JSONB scenario в плоские поля
        const sc = data.scenario || {};
        setForm(f => ({
          ...f,
          title: data.title || f.title,
          stratagema_title: data.stratagema_title || '',
          lifecycle_stage: data.lifecycle_stage || f.lifecycle_stage,
          lifecycle_description: data.lifecycle_description || '',
          lc_profit:    data.lc_profit    || autoFillLc(combination).lc_profit,
          lc_strategy:  data.lc_strategy  || autoFillLc(combination).lc_strategy,
          lc_decisions: data.lc_decisions || autoFillLc(combination).lc_decisions,
          lc_consumer:  data.lc_consumer  || autoFillLc(combination).lc_consumer,
          lc_market:    data.lc_market    || autoFillLc(combination).lc_market,
          lc_value:     data.lc_value     || autoFillLc(combination).lc_value,
          scenario_text: data.scenario_text || '',
          marketing_text: data.marketing_text || '',
          management_text: data.management_text || '',
          assm_planning: data.assm_planning || '',
          assm_growth: data.assm_growth || '',
          assm_advertising: data.assm_advertising || '',
          assm_feedback: data.assm_feedback || '',
          assm_risk: data.assm_risk || '',
          assm_product: data.assm_product || '',
          assm_service: data.assm_service || '',
          assm_startup: data.assm_startup || '',
          assm_investment: data.assm_investment || '',
          assm_contracts: data.assm_contracts || '',
          assm_sync: data.assm_sync || '',
          assm_creative: data.assm_creative || '',
          assm_interaction: data.assm_interaction || '',
          transition_title: data.transition_title || f.transition_title,
          transition_lifecycle_stage: data.transition_lifecycle_stage || f.transition_lifecycle_stage,
          transition_description: data.transition_description || '',
          is_published: data.is_published || false,
          scenario_innovation_strategy: sc.innovation_strategy || '',
          scenario_innovation_type: sc.innovation_type || '',
          scenario_value_discipline: sc.value_discipline || '',
          scenario_leadership_principles: sc.leadership_principles || '',
          scenario_growth_strategy: sc.growth_strategy || '',
          scenario_focus: sc.focus || '',
        }));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [combination]);

  const set = (k: string, v: string | boolean) => { setForm(f => ({ ...f, [k]: v })); setSaved(false); };

  const save = async (publish: boolean) => {
    setSaving(true); setError('');
    try {
      const body: any = {
        title: form.title,
        stratagema_title: form.stratagema_title,
        lifecycle_stage: form.lifecycle_stage,
        lifecycle_description: form.lifecycle_description,
        lc_profit:    form.lc_profit,
        lc_strategy:  form.lc_strategy,
        lc_decisions: form.lc_decisions,
        lc_consumer:  form.lc_consumer,
        lc_market:    form.lc_market,
        lc_value:     form.lc_value,
        scenario_text: form.scenario_text,
        marketing_text: form.marketing_text,
        management_text: form.management_text,
        assm_planning: form.assm_planning,
        assm_growth: form.assm_growth,
        assm_advertising: form.assm_advertising,
        assm_feedback: form.assm_feedback,
        assm_risk: form.assm_risk,
        assm_product: form.assm_product,
        assm_service: form.assm_service,
        assm_startup: form.assm_startup,
        assm_investment: form.assm_investment,
        assm_contracts: form.assm_contracts,
        assm_sync: form.assm_sync,
        assm_creative: form.assm_creative,
        assm_interaction: form.assm_interaction,
        transition_title: form.transition_title,
        transition_lifecycle_stage: form.transition_lifecycle_stage,
        transition_description: form.transition_description,
        is_published: publish,
        // Собираем JSONB scenario
        scenario: {
          innovation_strategy: form.scenario_innovation_strategy,
          innovation_type: form.scenario_innovation_type,
          value_discipline: form.scenario_value_discipline,
          leadership_principles: form.scenario_leadership_principles,
          growth_strategy: form.scenario_growth_strategy,
          focus: form.scenario_focus,
        },
        // current_state заполняется автоматически из комбинации
        current_state: {
          combination: combination,
          hex_name: hex?.name || '',
        },
      };

      const r = await fetch(`/api/admin/strategies/combo/${combination}`, {
        method: 'PUT', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Ошибка сохранения'); }
      const data = await r.json();
      setForm(f => ({ ...f, is_published: data.is_published }));
      setSaved(true);
    } catch (e: any) { setError(e.message || 'Ошибка'); }
    finally { setSaving(false); }
  };

  const inp = { width: '100%', padding: '10px 14px', border: '1px solid rgba(26,37,64,0.18)', borderRadius: 6, fontFamily: 'sans-serif', fontSize: 13, background: '#fafaf8', color: '#1a2540', outline: 'none', boxSizing: 'border-box' as const };
  const lbl = { display: 'block', fontFamily: 'sans-serif', fontSize: 11, fontWeight: 600 as const, letterSpacing: 1, textTransform: 'uppercase' as const, color: 'rgba(26,37,64,0.5)', marginBottom: 6 };
  const btn = (extra: React.CSSProperties = {}) => ({ padding: '9px 18px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontFamily: 'sans-serif', ...extra } as const);

  const FI = ({ label, k, ph = '' }: { label: string; k: string; ph?: string }) => (
    <div style={{ marginBottom: 16 }}>
      {label && <label style={lbl}>{label}</label>}
      <input value={(form as any)[k] || ''} onChange={e => set(k, e.target.value)} placeholder={ph} style={inp} />
    </div>
  );

  const FA = ({ label, k, rows = 4, ph = '' }: { label: string; k: string; rows?: number; ph?: string }) => (
    <div style={{ marginBottom: 16 }}>
      {label && <label style={lbl}>{label}</label>}
      <textarea value={(form as any)[k] || ''} onChange={e => set(k, e.target.value)} rows={rows} placeholder={ph}
        style={{ ...inp, resize: 'vertical', lineHeight: 1.6 }} />
    </div>
  );

  const Sec = ({ label, title, help, children }: { label: string; title: string; help: string; children: React.ReactNode }) => (
    <div style={{ background: '#fff', borderRadius: 10, border: '1px solid rgba(26,37,64,0.1)', padding: '24px 28px', marginBottom: 20 }}>
      <span style={{ fontFamily: 'sans-serif', fontSize: 10, fontWeight: 700, letterSpacing: 2, textTransform: 'uppercase', color: '#c0392b' }}>{label}</span>
      <h3 style={{ fontFamily: 'Georgia, serif', fontSize: 18, color: '#1a2540', margin: '6px 0 4px' }}>{title}</h3>
      <p style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.4)', margin: '0 0 20px' }}>{help}</p>
      {children}
    </div>
  );

  if (loading) return <div style={{ padding: 40, fontFamily: 'sans-serif', color: 'rgba(26,37,64,0.4)' }}>Загрузка…</div>;
  if (!hex) return (
    <div style={{ padding: 40, fontFamily: 'sans-serif', color: '#1a2540' }}>
      <p>Комбинация <strong>{combination}</strong> не найдена.</p>
      <button onClick={() => router.push('/admin/strategies')} style={btn({ border: '1px solid rgba(26,37,64,0.2)', background: 'transparent', color: '#1a2540' })}>← К списку</button>
    </div>
  );

  const targetHex = getTargetHex(combination);

  return (
    <div style={{ padding: '32px 40px', maxWidth: 880, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <span style={{ fontFamily: 'sans-serif', fontSize: 11, letterSpacing: 2, textTransform: 'uppercase', color: '#c0392b', fontWeight: 600 }}>
            Стратегия №{hex.n} · {combination}
          </span>
          <h1 style={{ fontFamily: 'Georgia, serif', fontSize: 24, margin: '4px 0 4px', color: '#1a2540', display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 40 }}>{comboToHex(combination)}</span>{form.title || hex.name}
          </h1>
          <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.5)', margin: 0 }}>Стадия: {hex.stage}</p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <button onClick={() => router.push('/admin/strategies')} style={btn({ border: '1px solid rgba(26,37,64,0.2)', background: 'transparent', color: '#1a2540' })}>← К списку</button>
          <button onClick={() => save(false)} disabled={saving} style={btn({ border: '1px solid rgba(26,37,64,0.2)', background: 'transparent', color: '#1a2540' })}>Черновик</button>
          <button onClick={() => save(true)} disabled={saving} style={btn({ border: 'none', background: '#1a2540', color: '#fff', fontWeight: 600 })}>
            {saving ? 'Сохранение…' : 'Сохранить и опубликовать'}
          </button>
        </div>
      </div>

      {saved && <div style={{ background: 'rgba(22,101,52,0.08)', border: '1px solid rgba(22,101,52,0.2)', borderRadius: 8, padding: '11px 16px', fontFamily: 'sans-serif', fontSize: 13, color: '#166534', marginBottom: 16 }}>✓ Сохранено успешно</div>}
      {error && <div style={{ background: 'rgba(153,27,27,0.08)', border: '1px solid rgba(153,27,27,0.2)', borderRadius: 8, padding: '11px 16px', fontFamily: 'sans-serif', fontSize: 13, color: '#991b1b', marginBottom: 16 }}>{error}</div>}

      {/* Визуал комбинации + целевая */}
      <div style={{ background: '#fff', borderRadius: 10, border: '1px solid rgba(26,37,64,0.1)', padding: '18px 24px', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 56, lineHeight: 1, color: '#1e3a8a', flexShrink: 0 }}>{comboToHex(combination)}</span>
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ display: 'flex', gap: 5, marginBottom: 8 }}>
            {combination.split('').map((c, i) => (
              <div key={i} style={{ width: 32, height: 32, borderRadius: 5, display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: 'monospace', fontSize: 13, fontWeight: 700,
                background: c === 'A' ? '#1e3a8a' : '#e8e4db', color: c === 'A' ? '#fff' : '#1a2540',
                border: c === 'B' ? '1px solid rgba(26,37,64,0.2)' : 'none' }}>{c}</div>
            ))}
          </div>
          <p style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.4)', margin: 0 }}>
            Позиции 1–6: ответы A или B на вопросы диагностики
          </p>
        </div>
        {targetHex && (
          <div style={{ textAlign: 'center', flexShrink: 0, padding: '10px 16px', background: 'rgba(26,37,64,0.03)', borderRadius: 8, border: '1px solid rgba(26,37,64,0.08)' }}>
            <div style={{ fontFamily: 'sans-serif', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1, color: 'rgba(26,37,64,0.4)', marginBottom: 4 }}>Целевая →</div>
            <span style={{ fontSize: 28, color: '#1e3a8a', display: 'block', lineHeight: 1, marginBottom: 4 }}>{String.fromCodePoint(0x4DC0 + targetHex.n - 1)}</span>
            <div style={{ fontFamily: 'sans-serif', fontSize: 11, color: '#1e3a8a', fontWeight: 600, marginBottom: 2 }}>Гексаграмма {targetHex.n}</div>
            <div style={{ fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.6)' }}>{targetHex.name}</div>
          </div>
        )}
        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          <div style={{ fontFamily: 'sans-serif', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, color: 'rgba(26,37,64,0.35)', marginBottom: 6 }}>Статус</div>
          <span style={{ display: 'inline-block', padding: '4px 14px', borderRadius: 99, fontSize: 12, fontWeight: 600,
            background: form.is_published ? 'rgba(22,101,52,0.1)' : 'rgba(26,37,64,0.08)',
            color: form.is_published ? '#166534' : 'rgba(26,37,64,0.5)' }}>
            {form.is_published ? 'Опубликовано' : 'Черновик'}
          </span>
        </div>
      </div>

      {/* Секции */}
      <Sec label="Основное" title="Заголовок и стратагема" help="Отображается в шапке отчёта пользователя.">
        <FI label="Заголовок стратегии" k="title" ph={hex.name} />
        <FI label="Стратагема (название)" k="stratagema_title" ph="Краткая формулировка стратагемы" />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div>
            <label style={lbl}>Стадия жизненного цикла</label>
            <select value={(form as any).lifecycle_stage || hex.stage} onChange={e => set('lifecycle_stage', e.target.value)} style={inp}>
              {['Зарождение','Расцвет','Зрелость','Обновление','Упадок'].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>
      </Sec>

      <Sec label="Жизненный цикл" title="Описание стадии" help="Блок 02 отчёта — 6 параметров диагностики. Авто-заполнены из комбинации, можно отредактировать.">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          {LC_BLOCKS.map((b, i) => (
            <div key={b.key} style={{ background: 'rgba(26,37,64,0.02)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: '14px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span style={{ width: 22, height: 22, borderRadius: '50%', background: combination[i] === 'A' ? '#1e3a8a' : '#e8e4db', color: combination[i] === 'A' ? '#fff' : '#1a2540', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'monospace', fontSize: 11, fontWeight: 700, flexShrink: 0, border: combination[i] === 'B' ? '1px solid rgba(26,37,64,0.2)' : 'none' }}>{combination[i]}</span>
                <label style={{ ...lbl, margin: 0 }}>{b.label}</label>
              </div>
              <textarea
                value={(form as any)[b.key] || ''}
                onChange={e => set(b.key, e.target.value)}
                rows={3}
                style={{ ...inp, resize: 'vertical', lineHeight: 1.6, fontSize: 12 }}
              />
            </div>
          ))}
        </div>
      </Sec>

      <Sec label="Сценарий" title="Сценарий развития" help="Блок 03 отчёта — что означает эта комбинация для бизнеса.">
        <FA label="" k="scenario_text" rows={5} ph="Опишите сценарий развития для данной комбинации…" />
      </Sec>

      <Sec label="Маркетинг" title="Рекомендации по маркетингу" help="Что делать с продуктом, ценой, каналами и коммуникацией.">
        <FA label="" k="marketing_text" rows={6} ph="Опишите маркетинговые рекомендации…" />
      </Sec>

      <Sec label="Управление" title="Рекомендации по управлению" help="Как организовать команду и принятие решений.">
        <FA label="" k="management_text" rows={6} ph="Опишите управленческие рекомендации…" />
      </Sec>

      <Sec label="Предположение для связи с будущим" title="Предположения, лежащие в основе принятия решения" help="Тематические блоки — отображаются в отчёте после раздела «Управление».">
        <FA label="Планирование" k="assm_planning" rows={3} ph="Предположения по планированию…" />
        <FA label="Рост и производительность" k="assm_growth" rows={3} ph="Предположения по росту и производительности…" />
        <FA label="Реклама" k="assm_advertising" rows={3} ph="Предположения по рекламе…" />
        <FA label="Братная связь" k="assm_feedback" rows={3} ph="Предположения по братной связи…" />
        <FA label="Риск" k="assm_risk" rows={3} ph="Предположения по рискам…" />
        <FA label="Выбор продукта" k="assm_product" rows={3} ph="Предположения по выбору продукта…" />
        <FA label="Сервис" k="assm_service" rows={3} ph="Предположения по сервису…" />
        <FA label="Стартап" k="assm_startup" rows={3} ph="Предположения по стартапу…" />
        <FA label="Инвестиции и финансы" k="assm_investment" rows={3} ph="Предположения по инвестициям и финансам…" />
        <FA label="Договора и соглашения" k="assm_contracts" rows={3} ph="Предположения по договорам и соглашениям…" />
        <FA label="Синхронизация" k="assm_sync" rows={3} ph="Предположения по синхронизации…" />
        <FA label="Творческий вклад" k="assm_creative" rows={3} ph="Предположения по творческому вкладу…" />
        <FA label="Взаимодействие" k="assm_interaction" rows={3} ph="Предположения по взаимодействию…" />
      </Sec>

      <Sec label="Переход" title="Целевое состояние" help="Куда компании двигаться — определено автоматически по таблице соответствия гексаграмм.">
        {targetHex && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 20, background: 'rgba(192,57,43,0.04)', border: '1px solid rgba(192,57,43,0.18)', borderRadius: 10, padding: '16px 20px', marginBottom: 20 }}>
            <div style={{ textAlign: 'center', flexShrink: 0 }}>
              <div style={{ fontSize: 64, lineHeight: 1, color: '#1a2540', marginBottom: 4 }}>{String.fromCodePoint(0x4DC0 + targetHex.n - 1)}</div>
              <div style={{ fontFamily: 'sans-serif', fontSize: 10, color: '#c0392b', letterSpacing: 1, fontWeight: 700, textTransform: 'uppercase' }}>Гексаграмма {targetHex.n}</div>
              <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.7)', marginTop: 2 }}>{targetHex.name}</div>
              <div style={{ fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.4)', marginTop: 2 }}>{targetHex.stage}</div>
            </div>
            <div>
              <div style={{ fontFamily: 'sans-serif', fontSize: 11, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', color: 'rgba(26,37,64,0.4)', marginBottom: 4 }}>Целевая гексаграмма</div>
              <div style={{ fontFamily: 'Georgia, serif', fontSize: 18, color: '#1a2540', marginBottom: 4 }}>{targetHex.name}</div>
              <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#1e3a8a', letterSpacing: 2, marginBottom: 4 }}>{targetHex.combo}</div>
              <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.5)' }}>Стадия: {targetHex.stage}</div>
            </div>
          </div>
        )}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <FI label="Название перехода" k="transition_title" ph="Название целевой стратегии" />
          <div>
            <label style={lbl}>Стадия целевого состояния</label>
            <select value={(form as any).transition_lifecycle_stage} onChange={e => set('transition_lifecycle_stage', e.target.value)} style={inp}>
              {['','Зарождение','Расцвет','Зрелость','Обновление','Упадок'].map(s => <option key={s} value={s}>{s || '—'}</option>)}
            </select>
          </div>
        </div>
        <FA label="Описание перехода" k="transition_description" rows={4} ph="Опишите как компании перейти к целевому состоянию…" />
      </Sec>

      <Sec label="Сценарий стратагемы" title="Таблица стратагемы" help="Конкретные характеристики — отображаются в блоке «Сценарий стратагемы» отчёта.">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <FI label="Стратегия изменений" k="scenario_innovation_strategy" />
          <FI label="Тип изменений" k="scenario_innovation_type" />
          <FI label="Ценностная дисциплина" k="scenario_value_discipline" />
          <FI label="Принципы лидерства" k="scenario_leadership_principles" />
          <FI label="Стратегия роста" k="scenario_growth_strategy" />
          <FI label="Фокус" k="scenario_focus" />
        </div>
      </Sec>

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, paddingTop: 4, paddingBottom: 40 }}>
        <button onClick={() => save(false)} disabled={saving} style={btn({ border: '1px solid rgba(26,37,64,0.2)', background: 'transparent', color: '#1a2540' })}>Сохранить черновик</button>
        <button onClick={() => save(true)} disabled={saving} style={btn({ border: 'none', background: '#1a2540', color: '#fff', fontWeight: 600 })}>Сохранить и опубликовать</button>
      </div>
    </div>
  );
}
