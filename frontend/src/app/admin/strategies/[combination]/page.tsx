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

// Поля точно соответствуют модели Strategy в БД
const EMPTY = {
  title: '',
  stratagema_title: '',
  lifecycle_stage: '',
  lifecycle_description: '',
  scenario_text: '',
  marketing_text: '',
  management_text: '',
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
    // Pre-fill из статических данных
    setForm(f => ({
      ...f,
      title: hex.name,
      lifecycle_stage: hex.stage,
    }));
    fetch(`/api/strategies/${combination}`, { credentials: 'include' })
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
          scenario_text: data.scenario_text || '',
          marketing_text: data.marketing_text || '',
          management_text: data.management_text || '',
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
        scenario_text: form.scenario_text,
        marketing_text: form.marketing_text,
        management_text: form.management_text,
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

      const r = await fetch(`/api/strategies/${combination}`, {
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

  const targetHex = null;

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
            <span style={{ fontSize: 28, color: '#1e3a8a', display: 'block', lineHeight: 1, marginBottom: 4 }}>{comboToHex(form.transition_title || '')}</span>
            <div style={{ fontFamily: 'monospace', fontSize: 11, color: 'rgba(26,37,64,0.5)', marginBottom: 2 }}>{form.transition_title}</div>
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

      <Sec label="Жизненный цикл" title="Описание стадии" help="Блок 02 отчёта — характеристика текущей фазы компании.">
        <FA label="" k="lifecycle_description" rows={5} ph="Опишите текущую фазу жизненного цикла компании…" />
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

      <Sec label="Переход" title="Целевое состояние" help="Куда компании двигаться — предзаполнено из таблицы соответствия.">
        <div style={{ background: 'rgba(30,58,138,0.04)', border: '1px solid rgba(30,58,138,0.12)', borderRadius: 8, padding: '12px 16px', marginBottom: 16, fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.6)' }}>
          Укажите комбинацию и название целевой стратегии, к которой должна перейти компания.
        </div>
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
          <FI label="Инновационная стратегия" k="scenario_innovation_strategy" />
          <FI label="Инновационный тип" k="scenario_innovation_type" />
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
