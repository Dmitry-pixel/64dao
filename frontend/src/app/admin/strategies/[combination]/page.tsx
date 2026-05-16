'use client';

import { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';

const HEXAGRAM_DATA = [
  { n:  1, combo: 'AAAAAA', char: '䷀', name: 'Действие',              stage: 'Расцвет',     target_combo: 'AABAAA', target_n:  9, target_name: 'Развитие' },
  { n:  2, combo: 'AAAAAB', char: '䷁', name: 'Реакция',               stage: 'Зарождение',  target_combo: 'BBBBAB', target_n: 62, target_name: 'Точность' },
  { n:  3, combo: 'AAAABA', char: '䷂', name: 'Появление',             stage: 'Зарождение',  target_combo: 'BBAAAA', target_n: 49, target_name: 'Реформа' },
  { n:  4, combo: 'AAAABB', char: '䷃', name: 'Формализация',          stage: 'Зарождение',  target_combo: 'AAABBA', target_n:  7, target_name: 'Управление' },
  { n:  5, combo: 'AAABAA', char: '䷄', name: 'Бдительность',          stage: 'Расцвет',     target_combo: 'BBBBBA', target_n: 63, target_name: 'Завершение' },
  { n:  6, combo: 'AAABAB', char: '䷅', name: 'Раздор',                stage: 'Упадок',      target_combo: 'AAABAB', target_n:  6, target_name: 'Раздор' },
  { n:  7, combo: 'AAABBA', char: '䷆', name: 'Управление',            stage: 'Зарождение',  target_combo: 'BBBBAB', target_n: 62, target_name: 'Точность' },
  { n:  8, combo: 'AAABBB', char: '䷇', name: 'Объединение',           stage: 'Зарождение',  target_combo: 'ABABBA', target_n: 23, target_name: 'Разрушение' },
  { n:  9, combo: 'AABAAA', char: '䷈', name: 'Развитие',              stage: 'Расцвет',     target_combo: 'BAABAA', target_n: 37, target_name: 'Гармония' },
  { n: 10, combo: 'AABAAB', char: '䷉', name: 'Последовательность',    stage: 'Расцвет',     target_combo: 'ABBAAA', target_n: 25, target_name: 'Естественность' },
  { n: 11, combo: 'AABABA', char: '䷊', name: 'Достижение',            stage: 'Расцвет',     target_combo: 'BAAABB', target_n: 36, target_name: 'Неблагоприятный' },
  { n: 12, combo: 'AABABB', char: '䷋', name: 'Препятствие',           stage: 'Упадок',      target_combo: 'AABAAA', target_n:  9, target_name: 'Развитие' },
  { n: 13, combo: 'AABBAA', char: '䷌', name: 'Осознанность',          stage: 'Расцвет',     target_combo: 'BAABAA', target_n: 37, target_name: 'Гармония' },
  { n: 14, combo: 'AABBAB', char: '䷍', name: 'Процветание',           stage: 'Расцвет',     target_combo: 'ABBAAB', target_n: 26, target_name: 'Изобилие' },
  { n: 15, combo: 'AABBBA', char: '䷎', name: 'Смирение',              stage: 'Обновление',  target_combo: 'AABABA', target_n: 11, target_name: 'Достижение' },
  { n: 16, combo: 'AABBBB', char: '䷏', name: 'Радость',               stage: 'Расцвет',     target_combo: 'BBABAB', target_n: 54, target_name: 'Амбиции' },
  { n: 17, combo: 'ABAAAA', char: '䷐', name: 'Соответствие',          stage: 'Обновление',  target_combo: 'BBBBBA', target_n: 63, target_name: 'Завершение' },
  { n: 18, combo: 'ABAAAB', char: '䷑', name: 'Диссонанс',             stage: 'Обновление',  target_combo: 'BBBBBB', target_n: 64, target_name: 'Незавершённость' },
  { n: 19, combo: 'ABAABA', char: '䷒', name: 'Подход',                stage: 'Расцвет',     target_combo: 'BAAAAB', target_n: 34, target_name: 'Сила' },
  { n: 20, combo: 'ABAABB', char: '䷓', name: 'Наблюдать',             stage: 'Обновление',  target_combo: 'BAAAAA', target_n: 33, target_name: 'Благоразумие' },
  { n: 21, combo: 'ABABAA', char: '䷔', name: 'Устранять',             stage: 'Упадок',      target_combo: 'BBBBBB', target_n: 64, target_name: 'Незавершённость' },
  { n: 22, combo: 'ABABAB', char: '䷕', name: 'Изящество',             stage: 'Расцвет',     target_combo: 'ABAAAB', target_n: 18, target_name: 'Диссонанс' },
  { n: 23, combo: 'ABABBA', char: '䷖', name: 'Разрушение',            stage: 'Упадок',      target_combo: 'BBABBB', target_n: 56, target_name: 'Стимулирование' },
  { n: 24, combo: 'ABABBB', char: '䷗', name: 'Возрождение',           stage: 'Зарождение',  target_combo: 'ABAABA', target_n: 19, target_name: 'Подход' },
  { n: 25, combo: 'ABBAAA', char: '䷘', name: 'Естественность',        stage: 'Расцвет',     target_combo: 'BAABAA', target_n: 37, target_name: 'Гармония' },
  { n: 26, combo: 'ABBAAB', char: '䷙', name: 'Изобилие',              stage: 'Обновление',  target_combo: 'ABABAB', target_n: 22, target_name: 'Изящество' },
  { n: 27, combo: 'ABBABA', char: '䷚', name: 'Умеренность',           stage: 'Зарождение',  target_combo: 'AAAABB', target_n:  4, target_name: 'Формализация' },
  { n: 28, combo: 'ABBABB', char: '䷛', name: 'Избыток',               stage: 'Обновление',  target_combo: 'BABABB', target_n: 44, target_name: 'Встреча' },
  { n: 29, combo: 'ABBBAA', char: '䷜', name: 'Решимость',             stage: 'Упадок',      target_combo: 'AAAABA', target_n:  3, target_name: 'Появление' },
  { n: 30, combo: 'ABBBAB', char: '䷝', name: 'Великолепие',           stage: 'Зрелость',    target_combo: 'ABABAB', target_n: 22, target_name: 'Изящество' },
  { n: 31, combo: 'ABBBBA', char: '䷞', name: 'Влияние',               stage: 'Расцвет',     target_combo: 'BABABA', target_n: 43, target_name: 'Прорыв' },
  { n: 32, combo: 'ABBBBB', char: '䷟', name: 'Выносливость',          stage: 'Зарождение',  target_combo: 'BABABB', target_n: 44, target_name: 'Встреча' },
  { n: 33, combo: 'BAAAAA', char: '䷠', name: 'Благоразумие',          stage: 'Упадок',      target_combo: 'AAAAAA', target_n:  1, target_name: 'Действие' },
  { n: 34, combo: 'BAAAAB', char: '䷡', name: 'Сила',                  stage: 'Расцвет',     target_combo: 'AAAAAA', target_n:  1, target_name: 'Действие' },
  { n: 35, combo: 'BAAABA', char: '䷢', name: 'Благоприятный',         stage: 'Расцвет',     target_combo: 'BBBBBB', target_n: 64, target_name: 'Незавершённость' },
  { n: 36, combo: 'BAAABB', char: '䷣', name: 'Неблагоприятный',       stage: 'Упадок',      target_combo: 'BAABAA', target_n: 37, target_name: 'Гармония' },
  { n: 37, combo: 'BAABAA', char: '䷤', name: 'Гармония',              stage: 'Зарождение',  target_combo: 'BBBBBA', target_n: 63, target_name: 'Завершение' },
  { n: 38, combo: 'BAABAB', char: '䷥', name: 'Полярность',            stage: 'Упадок',      target_combo: 'ABABAA', target_n: 21, target_name: 'Устранять' },
  { n: 39, combo: 'BAABBA', char: '䷦', name: 'Трудность',             stage: 'Упадок',      target_combo: 'AAABAA', target_n:  5, target_name: 'Бдительность' },
  { n: 40, combo: 'BAABBB', char: '䷧', name: 'Избавление',            stage: 'Обновление',  target_combo: 'BABBAB', target_n: 46, target_name: 'Самоотдача' },
  { n: 41, combo: 'BABAAA', char: '䷨', name: 'Убыток',                stage: 'Упадок',      target_combo: 'ABBABA', target_n: 27, target_name: 'Умеренность' },
  { n: 42, combo: 'BABAAB', char: '䷩', name: 'Прибыль',               stage: 'Расцвет',     target_combo: 'AAAABA', target_n:  3, target_name: 'Появление' },
  { n: 43, combo: 'BABABA', char: '䷪', name: 'Прорыв',                stage: 'Расцвет',     target_combo: 'AAABAA', target_n:  5, target_name: 'Бдительность' },
  { n: 44, combo: 'BABABB', char: '䷫', name: 'Встреча',               stage: 'Расцвет',     target_combo: 'BAAAAA', target_n: 33, target_name: 'Благоразумие' },
  { n: 45, combo: 'BABBAA', char: '䷬', name: 'Объединение',           stage: 'Зарождение',  target_combo: 'BBBAAB', target_n: 58, target_name: 'Бодрость' },
  { n: 46, combo: 'BABBAB', char: '䷭', name: 'Самоотдача',            stage: 'Расцвет',     target_combo: 'BBBAAA', target_n: 57, target_name: 'Интуиция' },
  { n: 47, combo: 'BABBBA', char: '䷮', name: 'Понимание',             stage: 'Упадок',      target_combo: 'BABABB', target_n: 44, target_name: 'Встреча' },
  { n: 48, combo: 'BABBBB', char: '䷯', name: 'Глубина',               stage: 'Обновление',  target_combo: 'BABBBA', target_n: 47, target_name: 'Понимание' },
  { n: 49, combo: 'BBAAAA', char: '䷰', name: 'Реформа',               stage: 'Обновление',  target_combo: 'BBBBBA', target_n: 63, target_name: 'Завершение' },
  { n: 50, combo: 'BBAAAB', char: '䷱', name: 'Ценности',              stage: 'Расцвет',     target_combo: 'ABAAAB', target_n: 18, target_name: 'Диссонанс' },
  { n: 51, combo: 'BBAABA', char: '䷲', name: 'Смелость',              stage: 'Зарождение',  target_combo: 'ABBAAA', target_n: 25, target_name: 'Естественность' },
  { n: 52, combo: 'BBAABB', char: '䷳', name: 'Сосредоточенность',     stage: 'Обновление',  target_combo: 'ABAAAB', target_n: 18, target_name: 'Диссонанс' },
  { n: 53, combo: 'BBABAA', char: '䷴', name: 'Готовность',            stage: 'Обновление',  target_combo: 'BAABBA', target_n: 39, target_name: 'Трудность' },
  { n: 54, combo: 'BBABAB', char: '䷵', name: 'Амбиции',               stage: 'Упадок',      target_combo: 'AABABA', target_n: 11, target_name: 'Достижение' },
  { n: 55, combo: 'BBABBA', char: '䷶', name: 'Изобилие',              stage: 'Расцвет',     target_combo: 'BAAABB', target_n: 36, target_name: 'Неблагоприятный' },
  { n: 56, combo: 'BBABBB', char: '䷷', name: 'Стимулирование',        stage: 'Упадок',      target_combo: 'AABBAB', target_n: 14, target_name: 'Процветание' },
  { n: 57, combo: 'BBBAAA', char: '䷸', name: 'Интуиция',              stage: 'Обновление',  target_combo: 'BABABB', target_n: 44, target_name: 'Встреча' },
  { n: 58, combo: 'BBBAAB', char: '䷹', name: 'Бодрость',              stage: 'Расцвет',     target_combo: 'AAABAA', target_n:  5, target_name: 'Бдительность' },
  { n: 59, combo: 'BBBABA', char: '䷺', name: 'Установление связей',   stage: 'Обновление',  target_combo: 'BABABB', target_n: 44, target_name: 'Встреча' },
  { n: 60, combo: 'BBBABB', char: '䷻', name: 'Реализм',               stage: 'Обновление',  target_combo: 'BABABA', target_n: 43, target_name: 'Прорыв' },
  { n: 61, combo: 'BBBBAA', char: '䷼', name: 'Внутренняя правда',     stage: 'Расцвет',     target_combo: 'BABAAB', target_n: 42, target_name: 'Прибыль' },
  { n: 62, combo: 'BBBBAB', char: '䷽', name: 'Точность',              stage: 'Упадок',      target_combo: 'BAAAAA', target_n: 33, target_name: 'Благоразумие' },
  { n: 63, combo: 'BBBBBA', char: '䷾', name: 'Завершение',            stage: 'Зрелость',    target_combo: 'ABAAAA', target_n: 17, target_name: 'Соответствие' },
  { n: 64, combo: 'BBBBBB', char: '䷿', name: 'Незавершённость',       stage: 'Зарождение',  target_combo: 'BAABBB', target_n: 40, target_name: 'Избавление' },
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

type Params = { params: Promise<{ combination: string }> };

export default function StrategyEditorPage({ params }: Params) {
  const router = useRouter();
  const { combination } = use(params);
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
      transition_title: hex.target_name,
      transition_lifecycle_stage: HEXAGRAM_MAP[hex.target_combo]?.stage || '',
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

  const targetHex = HEXAGRAM_MAP[hex.target_combo];

  return (
    <div style={{ padding: '32px 40px', maxWidth: 880, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <span style={{ fontFamily: 'sans-serif', fontSize: 11, letterSpacing: 2, textTransform: 'uppercase', color: '#c0392b', fontWeight: 600 }}>
            Стратегия №{hex.n} · {combination}
          </span>
          <h1 style={{ fontFamily: 'Georgia, serif', fontSize: 24, margin: '4px 0 4px', color: '#1a2540', display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 40 }}>{hex.char}</span>{form.title || hex.name}
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
        <span style={{ fontSize: 56, lineHeight: 1, color: '#1e3a8a', flexShrink: 0 }}>{hex.char}</span>
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
            <span style={{ fontSize: 28, color: '#1e3a8a', display: 'block', lineHeight: 1, marginBottom: 4 }}>{targetHex.char}</span>
            <div style={{ fontFamily: 'monospace', fontSize: 11, color: 'rgba(26,37,64,0.5)', marginBottom: 2 }}>{hex.target_combo}</div>
            <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: '#1a2540', fontWeight: 600 }}>{hex.target_name}</div>
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
          По таблице: <strong style={{ color: '#1a2540' }}>{hex.target_combo}</strong> — «{hex.target_name}». Можно изменить вручную.
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <FI label="Название перехода" k="transition_title" ph={hex.target_name} />
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
