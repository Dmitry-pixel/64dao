'use client';

import { useState, useEffect, useRef, useCallback, memo } from 'react';
import { useRouter } from 'next/navigation';
import { HEXAGRAM_DATA, HEXAGRAM_MAP, comboToHex } from '@/lib/hexagrams';



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

const LC_BLOCKS = [
  { key: 'lc_profit',    label: 'Формирование прибыли',
    a: 'Рост выручки и объёма продаж',
    b: 'Повышение эффективности, сокращение расходов и потерь' },
  { key: 'lc_strategy',  label: 'Рыночная стратегия',
    a: 'Быстрый последователь — адаптация уже подтверждённых решений. Быстро адаптирует и улучшает существующие решения',
    b: 'Первопроходец — создание новых решений и рынков. Создаёт новые категории, продукты или подходы' },
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
  LC_BLOCKS.forEach((b, i) => { result[b.key] = combination[i] === 'A' ? b.a : b.b; });
  return result;
}

function getTargetHex(combo: string) {
  const cur = HEXAGRAM_MAP[combo];
  if (!cur) return null;
  const targetN = TARGET_HEXAGRAM[cur.n];
  if (!targetN) return null;
  return HEXAGRAM_DATA.find(h => h.n === targetN) || null;
}

// ─── Стили ────────────────────────────────────────────────────────────────────
const S_INP: React.CSSProperties = {
  width: '100%', padding: '10px 14px',
  border: '1px solid rgba(26,37,64,0.3)', borderRadius: 6,
  fontFamily: 'sans-serif', fontSize: 13,
  background: '#fff', color: '#1a2540', boxSizing: 'border-box',
};
const S_TA: React.CSSProperties = { ...S_INP, resize: 'vertical', lineHeight: 1.6 };
const S_LBL: React.CSSProperties = {
  display: 'block', fontFamily: 'sans-serif', fontSize: 11, fontWeight: 600,
  letterSpacing: 1, textTransform: 'uppercase', color: 'rgba(26,37,64,0.5)', marginBottom: 6,
};

type OnChange = (k: string, v: string) => void;

// ─── Uncontrolled компоненты (defaultValue — без потери фокуса) ───────────────
const FI = memo(function FI({ label, fk, dv, ph = '', onChange }: {
  label: string; fk: string; dv: string; ph?: string; onChange: OnChange;
}) {
  return (
    <div style={{ marginBottom: 16 }}>
      {label && <label style={S_LBL}>{label}</label>}
      <input defaultValue={dv} onChange={e => onChange(fk, e.target.value)} placeholder={ph} style={S_INP} />
    </div>
  );
});

const FA = memo(function FA({ label, fk, dv, rows = 4, ph = '', onChange }: {
  label: string; fk: string; dv: string; rows?: number; ph?: string; onChange: OnChange;
}) {
  return (
    <div style={{ marginBottom: 16 }}>
      {label && <label style={S_LBL}>{label}</label>}
      <textarea defaultValue={dv} onChange={e => onChange(fk, e.target.value)} rows={rows} placeholder={ph} style={S_TA} />
    </div>
  );
});

const Sec = memo(function Sec({ label, title, help, children }: {
  label: string; title: string; help: string; children: React.ReactNode;
}) {
  return (
    <div style={{ background: '#fff', borderRadius: 10, border: '1px solid rgba(26,37,64,0.1)', padding: '24px 28px', marginBottom: 20 }}>
      <span style={{ fontFamily: 'sans-serif', fontSize: 10, fontWeight: 700, letterSpacing: 2, textTransform: 'uppercase', color: '#c0392b' }}>{label}</span>
      <h3 style={{ fontFamily: 'Georgia, serif', fontSize: 18, color: '#1a2540', margin: '6px 0 4px' }}>{title}</h3>
      <p style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.4)', margin: '0 0 20px' }}>{help}</p>
      {children}
    </div>
  );
});

// ─── Типы ─────────────────────────────────────────────────────────────────────
type FormData = {
  title: string; stratagema_title: string; lifecycle_stage: string; lifecycle_description: string;
  lc_profit: string; lc_strategy: string; lc_decisions: string;
  lc_consumer: string; lc_market: string; lc_value: string;
  scenario_text: string; marketing_text: string; management_text: string;
  assm_planning: string; assm_growth: string; assm_advertising: string;
  assm_feedback: string; assm_risk: string; assm_product: string;
  assm_service: string; assm_startup: string; assm_investment: string;
  assm_contracts: string; assm_sync: string; assm_creative: string; assm_interaction: string;
  assm_resources: string; assm_research: string; assm_trade: string; assm_failures: string; assm_success: string;
  transition_title: string; transition_lifecycle_stage: string; transition_description: string;
  fin_pattern_essence: string; fin_pattern_mistake: string;
  scenario_innovation_strategy: string; scenario_innovation_type: string;
  scenario_value_discipline: string; scenario_leadership_principles: string;
  scenario_growth_strategy: string; scenario_focus: string;
};

const EMPTY_FORM: FormData = {
  title: '', stratagema_title: '', lifecycle_stage: '', lifecycle_description: '',
  lc_profit: '', lc_strategy: '', lc_decisions: '', lc_consumer: '', lc_market: '', lc_value: '',
  scenario_text: '', marketing_text: '', management_text: '',
  assm_planning: '', assm_growth: '', assm_advertising: '', assm_feedback: '', assm_risk: '',
  assm_product: '', assm_service: '', assm_startup: '', assm_investment: '',
  assm_contracts: '', assm_sync: '', assm_creative: '', assm_interaction: '',
  assm_resources: '', assm_research: '', assm_trade: '', assm_failures: '', assm_success: '',
  transition_title: '', transition_lifecycle_stage: '', transition_description: '',
  fin_pattern_essence: '', fin_pattern_mistake: '',
  scenario_innovation_strategy: '', scenario_innovation_type: '', scenario_value_discipline: '',
  scenario_leadership_principles: '', scenario_growth_strategy: '', scenario_focus: '',
};

// ─── Страница ─────────────────────────────────────────────────────────────────
export default function StrategyEditorPage({ params }: { params: { combination: string } }) {
  const router = useRouter();
  const { combination } = params;
  const hex = HEXAGRAM_MAP[combination];

  // formRef хранит все значения — изменения НЕ вызывают ре-рендер
  const formRef = useRef<FormData>({ ...EMPTY_FORM });

  // Только UI-состояние (saving/saved/error/published/selects) — НЕ содержимое полей
  const [loading, setLoading]         = useState(true);
  const [saving, setSaving]           = useState(false);
  const [saved, setSaved]             = useState(false);
  const [error, setError]             = useState('');
  const [isPublished, setIsPublished] = useState(false);
  const [lcStage, setLcStage]         = useState('');
  // formKey — меняется ОДИН РАЗ после загрузки, чтобы форма отрисовалась с правильными defaultValue
  const [formKey, setFormKey]         = useState(0);

  useEffect(() => {
    if (!hex) { setLoading(false); return; }
    const lc = autoFillLc(combination);

    fetch(`/api/admin/strategies/combo/${combination}`, { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data && !data.detail) {
          const sc = data.scenario || {};
          formRef.current = {
            title:                      data.title              || hex.name,
            stratagema_title:           data.stratagema_title   || '',
            lifecycle_stage:            data.lifecycle_stage    || '',
            lifecycle_description:      data.lifecycle_description || '',
            lc_profit:                  data.lc_profit          || lc.lc_profit,
            lc_strategy:                data.lc_strategy        || lc.lc_strategy,
            lc_decisions:               data.lc_decisions       || lc.lc_decisions,
            lc_consumer:                data.lc_consumer        || lc.lc_consumer,
            lc_market:                  data.lc_market          || lc.lc_market,
            lc_value:                   data.lc_value           || lc.lc_value,
            scenario_text:              data.scenario_text      || '',
            marketing_text:             data.marketing_text     || '',
            management_text:            data.management_text    || '',
            assm_planning:              data.assm_planning      || '',
            assm_growth:                data.assm_growth        || '',
            assm_advertising:           data.assm_advertising   || '',
            assm_feedback:              data.assm_feedback      || '',
            assm_risk:                  data.assm_risk          || '',
            assm_product:               data.assm_product       || '',
            assm_service:               data.assm_service       || '',
            assm_startup:               data.assm_startup       || '',
            assm_investment:            data.assm_investment    || '',
            assm_contracts:             data.assm_contracts     || '',
            assm_sync:                  data.assm_sync          || '',
            assm_creative:              data.assm_creative      || '',
            assm_interaction:           data.assm_interaction   || '',
            assm_resources:             data.assm_resources    || '',
            assm_research:              data.assm_research     || '',
            assm_trade:                 data.assm_trade        || '',
            assm_failures:              data.assm_failures     || '',
            assm_success:               data.assm_success      || '',
            fin_pattern_essence:        data.fin_pattern_essence || '',
            fin_pattern_mistake:        data.fin_pattern_mistake || '',
            transition_title:           data.transition_title   || '',
            transition_lifecycle_stage: data.transition_lifecycle_stage || '',
            transition_description:     data.transition_description    || '',
            scenario_innovation_strategy: sc.innovation_strategy  || '',
            scenario_innovation_type:     sc.innovation_type      || '',
            scenario_value_discipline:    sc.value_discipline     || '',
            scenario_leadership_principles: sc.leadership_principles || '',
            scenario_growth_strategy:   sc.growth_strategy || '',
            scenario_focus:             sc.focus           || '',
          };
          setIsPublished(data.is_published || false);
          setLcStage(data.lifecycle_stage || '');
        } else {
          formRef.current = { ...EMPTY_FORM, title: hex.name, lifecycle_stage: '', ...lc };
          setLcStage('');
        }
      })
      .catch(() => {
        formRef.current = { ...EMPTY_FORM, title: hex.name, lifecycle_stage: '', ...autoFillLc(combination) };
        setLcStage('');
      })
      .finally(() => {
        setFormKey(1);   // форма рендерится один раз с правильными данными
        setLoading(false);
      });
  }, [combination]);

  // onChange только пишет в ref — НИКАКИХ state-апдейтов → НИКАКОГО ре-рендера при вводе
  const handleChange = useCallback((k: string, v: string) => {
    (formRef.current as any)[k] = v;
  }, []);

  const save = async (publish: boolean) => {
    // Синхронизируем select-значения из state в ref перед сохранением
    formRef.current.lifecycle_stage = lcStage;

    setSaving(true); setError('');
    try {
      const f = formRef.current;
      const body = {
        title: f.title, stratagema_title: f.stratagema_title,
        lifecycle_stage: f.lifecycle_stage, lifecycle_description: f.lifecycle_description,
        lc_profit: f.lc_profit, lc_strategy: f.lc_strategy,
        lc_decisions: f.lc_decisions, lc_consumer: f.lc_consumer,
        lc_market: f.lc_market, lc_value: f.lc_value,
        scenario_text: f.scenario_text, marketing_text: f.marketing_text,
        management_text: f.management_text,
        assm_planning: f.assm_planning, assm_growth: f.assm_growth,
        assm_advertising: f.assm_advertising, assm_feedback: f.assm_feedback,
        assm_risk: f.assm_risk, assm_product: f.assm_product,
        assm_service: f.assm_service, assm_startup: f.assm_startup,
        assm_investment: f.assm_investment, assm_contracts: f.assm_contracts,
        assm_sync: f.assm_sync, assm_creative: f.assm_creative,
        assm_interaction: f.assm_interaction,
        assm_resources: f.assm_resources, assm_research: f.assm_research,
        assm_trade: f.assm_trade, assm_failures: f.assm_failures, assm_success: f.assm_success,
        fin_pattern_essence: f.fin_pattern_essence, fin_pattern_mistake: f.fin_pattern_mistake,
        transition_title: f.transition_title,
        transition_lifecycle_stage: f.transition_lifecycle_stage,
        transition_description: f.transition_description,
        is_published: publish,
        scenario: {
          innovation_strategy: f.scenario_innovation_strategy,
          innovation_type: f.scenario_innovation_type,
          value_discipline: f.scenario_value_discipline,
          leadership_principles: f.scenario_leadership_principles,
          growth_strategy: f.scenario_growth_strategy,
          focus: f.scenario_focus,
        },
        current_state: { combination, hex_name: hex?.name || '' },
      };
      const r = await fetch(`/api/admin/strategies/combo/${combination}`, {
        method: 'PUT', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Ошибка сохранения'); }
      const data = await r.json();
      setIsPublished(data.is_published);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e: any) { setError(e.message || 'Ошибка'); }
    finally { setSaving(false); }
  };

  const btn = (extra: React.CSSProperties = {}) =>
    ({ padding: '9px 18px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontFamily: 'sans-serif', ...extra } as const);

  if (loading) return <div style={{ padding: 40, fontFamily: 'sans-serif', color: 'rgba(26,37,64,0.4)' }}>Загрузка…</div>;
  if (!hex) return (
    <div style={{ padding: 40, fontFamily: 'sans-serif', color: '#1a2540' }}>
      <p>Комбинация <strong>{combination}</strong> не найдена.</p>
      <button onClick={() => router.push('/admin/strategies')} style={btn({ border: '1px solid rgba(26,37,64,0.2)', background: 'transparent', color: '#1a2540' })}>← К списку</button>
    </div>
  );

  const targetHex = getTargetHex(combination);
  const f = formRef.current;

  return (
    <div style={{ padding: '32px 40px', maxWidth: 880, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <span style={{ fontFamily: 'sans-serif', fontSize: 11, letterSpacing: 2, textTransform: 'uppercase', color: '#c0392b', fontWeight: 600 }}>
            Стратегия №{hex.n} · {combination}
          </span>
          <h1 style={{ fontFamily: 'Georgia, serif', fontSize: 24, margin: '4px 0 4px', color: '#1a2540', display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 40 }}>{comboToHex(combination)}</span>{f.title || hex.name}
          </h1>
          <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.5)', margin: 0 }}>Стадия: {lcStage || '—'}</p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <button onClick={() => router.push('/admin/strategies')} style={btn({ border: '1px solid rgba(26,37,64,0.2)', background: 'transparent', color: '#1a2540' })}>← К списку</button>
          <button onClick={() => save(false)} disabled={saving} style={btn({ border: '1px solid rgba(26,37,64,0.2)', background: 'transparent', color: '#1a2540' })}>{saving ? 'Сохранение…' : 'Черновик'}</button>
          <button onClick={() => save(true)} disabled={saving} style={btn({ border: 'none', background: '#1a2540', color: '#fff', fontWeight: 600 })}>{saving ? 'Сохранение…' : 'Сохранить и опубликовать'}</button>
        </div>
      </div>

      {saved && <div style={{ background: 'rgba(22,101,52,0.08)', border: '1px solid rgba(22,101,52,0.2)', borderRadius: 8, padding: '11px 16px', fontFamily: 'sans-serif', fontSize: 13, color: '#166534', marginBottom: 16 }}>✓ Сохранено успешно</div>}
      {error && <div style={{ background: 'rgba(153,27,27,0.08)', border: '1px solid rgba(153,27,27,0.2)', borderRadius: 8, padding: '11px 16px', fontFamily: 'sans-serif', fontSize: 13, color: '#991b1b', marginBottom: 16 }}>{error}</div>}

      {/* Визуал */}
      <div style={{ background: '#fff', borderRadius: 10, border: '1px solid rgba(26,37,64,0.1)', padding: '18px 24px', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 56, lineHeight: 1, color: '#1e3a8a', flexShrink: 0 }}>{comboToHex(combination)}</span>
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ display: 'flex', gap: 5, marginBottom: 8 }}>
            {combination.split('').map((c, i) => (
              <div key={i} style={{ width: 32, height: 32, borderRadius: 5, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'monospace', fontSize: 13, fontWeight: 700, background: c === 'A' ? '#1e3a8a' : '#e8e4db', color: c === 'A' ? '#fff' : '#1a2540', border: c === 'B' ? '1px solid rgba(26,37,64,0.2)' : 'none' }}>{c}</div>
            ))}
          </div>
          <p style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.4)', margin: 0 }}>Позиции 1–6: ответы A или B на вопросы диагностики</p>
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
          <span style={{ display: 'inline-block', padding: '4px 14px', borderRadius: 99, fontSize: 12, fontWeight: 600, background: isPublished ? 'rgba(22,101,52,0.1)' : 'rgba(26,37,64,0.08)', color: isPublished ? '#166534' : 'rgba(26,37,64,0.5)' }}>
            {isPublished ? 'Опубликовано' : 'Черновик'}
          </span>
        </div>
      </div>

      {/* ── Форма — key={formKey} гарантирует один рендер с правильными defaultValue ── */}
      <div key={formKey}>
        <Sec label="Основное" title="Заголовок и стратагема" help="Отображается в шапке отчёта пользователя.">
          <FI label="Заголовок стратегии" fk="title" dv={f.title} ph={hex.name} onChange={handleChange} />
          <FA label="Стратагема (название)" fk="stratagema_title" rows={3} dv={f.stratagema_title} ph="Краткая формулировка стратагемы" onChange={handleChange} />
          <div className="admin-form-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={S_LBL}>Стадия жизненного цикла</label>
              <select value={lcStage} onChange={e => setLcStage(e.target.value)} style={S_INP}>
                {['Зарождение','Расцвет','Зрелость','Обновление','Упадок'].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
        </Sec>

        <Sec label="Жизненный цикл" title="Описание стадии" help="6 параметров диагностики. Авто-заполнены из комбинации, можно отредактировать.">
          <div className="admin-form-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            {LC_BLOCKS.map((b, i) => (
              <div key={b.key} style={{ background: 'rgba(26,37,64,0.02)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: '14px 16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <span style={{ width: 22, height: 22, borderRadius: '50%', background: combination[i] === 'A' ? '#1e3a8a' : '#e8e4db', color: combination[i] === 'A' ? '#fff' : '#1a2540', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'monospace', fontSize: 11, fontWeight: 700, flexShrink: 0, border: combination[i] === 'B' ? '1px solid rgba(26,37,64,0.2)' : 'none' }}>{combination[i]}</span>
                  <label style={{ ...S_LBL, margin: 0 }}>{b.label}</label>
                </div>
                <FA label="" fk={b.key} dv={(f as any)[b.key] || ''} rows={3} onChange={handleChange} />
              </div>
            ))}
          </div>
        </Sec>

        <Sec label="Сценарий" title="Сценарий развития" help="Блок 03 отчёта — что означает эта комбинация для бизнеса.">
          <FA label="" fk="scenario_text" dv={f.scenario_text} rows={5} ph="Опишите сценарий развития…" onChange={handleChange} />
        </Sec>

        <Sec label="Маркетинг" title="Рекомендации по маркетингу" help="Что делать с продуктом, ценой, каналами и коммуникацией.">
          <FA label="" fk="marketing_text" dv={f.marketing_text} rows={6} ph="Опишите маркетинговые рекомендации…" onChange={handleChange} />
        </Sec>

        <Sec label="Управление" title="Рекомендации по управлению" help="Как организовать команду и принятие решений.">
          <FA label="" fk="management_text" dv={f.management_text} rows={6} ph="Опишите управленческие рекомендации…" onChange={handleChange} />
        </Sec>

        <Sec label="Финансовый паттерн" title="Паттерн гексаграммы (финансовая функция)" help="Используется в разделе «Финансовая функция» отчёта: суть — для текущей гексаграммы, ошибка — как предостережение целевого состояния.">
          <FA label="Суть ситуации (1–2 предложения)" fk="fin_pattern_essence" dv={f.fin_pattern_essence} rows={3} ph="Например: ресурс превышает ясность его применения; энергия системы ищет выход." onChange={handleChange} />
          <FA label="Типичная ошибка (1 предложение)" fk="fin_pattern_mistake" dv={f.fin_pattern_mistake} rows={3} ph="Например: активность ради активности — автоматизация без целевой модели." onChange={handleChange} />
        </Sec>

        <Sec label="Предположения" title="Предположения, лежащие в основе принятия решения" help="Тематические блоки — отображаются в отчёте после раздела «Управление».">
          <FA label="Планирование" fk="assm_planning" dv={f.assm_planning} rows={3} ph="Предположения по планированию…" onChange={handleChange} />
          <FA label="Рост и производительность" fk="assm_growth" dv={f.assm_growth} rows={3} ph="Предположения по росту…" onChange={handleChange} />
          <FA label="Реклама" fk="assm_advertising" dv={f.assm_advertising} rows={3} ph="Предположения по рекламе…" onChange={handleChange} />
          <FA label="Обратная связь" fk="assm_feedback" dv={f.assm_feedback} rows={3} ph="Предположения по обратной связи…" onChange={handleChange} />
          <FA label="Риск" fk="assm_risk" dv={f.assm_risk} rows={3} ph="Предположения по рискам…" onChange={handleChange} />
          <FA label="Выбор продукта" fk="assm_product" dv={f.assm_product} rows={3} ph="Предположения по выбору продукта…" onChange={handleChange} />
          <FA label="Сервис" fk="assm_service" dv={f.assm_service} rows={3} ph="Предположения по сервису…" onChange={handleChange} />
          <FA label="Стартап" fk="assm_startup" dv={f.assm_startup} rows={3} ph="Предположения по стартапу…" onChange={handleChange} />
          <FA label="Инвестиции и финансы" fk="assm_investment" dv={f.assm_investment} rows={3} ph="Предположения по инвестициям…" onChange={handleChange} />
          <FA label="Договора и соглашения" fk="assm_contracts" dv={f.assm_contracts} rows={3} ph="Предположения по договорам…" onChange={handleChange} />
          <FA label="Синхронизация" fk="assm_sync" dv={f.assm_sync} rows={3} ph="Предположения по синхронизации…" onChange={handleChange} />
          <FA label="Творческий вклад" fk="assm_creative" dv={f.assm_creative} rows={3} ph="Предположения по творческому вкладу…" onChange={handleChange} />
          <FA label="Взаимодействие" fk="assm_interaction" dv={f.assm_interaction} rows={3} ph="Предположения по взаимодействию…" onChange={handleChange} />
          <FA label="Достаточность ресурсов" fk="assm_resources" dv={f.assm_resources} rows={3} ph="Предположения по достаточности ресурсов…" onChange={handleChange} />
          <FA label="Исследование и разработка" fk="assm_research" dv={f.assm_research} rows={3} ph="Предположения по исследованиям и разработке…" onChange={handleChange} />
          <FA label="Международная торговля" fk="assm_trade" dv={f.assm_trade} rows={3} ph="Предположения по международной торговле…" onChange={handleChange} />
          <FA label="Источники неудач" fk="assm_failures" dv={f.assm_failures} rows={3} ph="Предположения по источникам неудач…" onChange={handleChange} />
          <FA label="Источники удачи" fk="assm_success" dv={f.assm_success} rows={3} ph="Предположения по источникам удачи…" onChange={handleChange} />
        </Sec>

        <Sec label="Переход" title="Целевое состояние" help="Куда компании двигаться — определено автоматически по таблице соответствия гексаграмм.">
          {targetHex && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 20, background: 'rgba(192,57,43,0.04)', border: '1px solid rgba(192,57,43,0.18)', borderRadius: 10, padding: '16px 20px', marginBottom: 20 }}>
              <div style={{ textAlign: 'center', flexShrink: 0 }}>
                <div style={{ fontSize: 64, lineHeight: 1, color: '#1a2540', marginBottom: 4 }}>{String.fromCodePoint(0x4DC0 + targetHex.n - 1)}</div>
                <div style={{ fontFamily: 'sans-serif', fontSize: 10, color: '#c0392b', letterSpacing: 1, fontWeight: 700, textTransform: 'uppercase' }}>Гексаграмма {targetHex.n}</div>
                <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.7)', marginTop: 2 }}>{targetHex.name}</div>
              </div>
              <div>
                <div style={{ fontFamily: 'sans-serif', fontSize: 11, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', color: 'rgba(26,37,64,0.4)', marginBottom: 4 }}>Целевая гексаграмма</div>
                <div style={{ fontFamily: 'Georgia, serif', fontSize: 18, color: '#1a2540', marginBottom: 4 }}>{targetHex.name}</div>
                <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#1e3a8a', letterSpacing: 2, marginBottom: 4 }}>{targetHex.combo}</div>
              </div>
            </div>
          )}
          <FA label="Описание перехода" fk="transition_description" dv={f.transition_description} rows={4} ph="Опишите как компании перейти к целевому состоянию…" onChange={handleChange} />
        </Sec>

        <Sec label="Сценарий стратагемы" title="Таблица стратагемы" help="Конкретные характеристики — отображаются в блоке «Сценарий стратагемы» отчёта.">
          <div className="admin-form-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <FI label="Стратегия изменений" fk="scenario_innovation_strategy" dv={f.scenario_innovation_strategy} onChange={handleChange} />
            <FI label="Тип изменений" fk="scenario_innovation_type" dv={f.scenario_innovation_type} onChange={handleChange} />
            <FI label="Ценностная дисциплина" fk="scenario_value_discipline" dv={f.scenario_value_discipline} onChange={handleChange} />
            <FI label="Принципы лидерства" fk="scenario_leadership_principles" dv={f.scenario_leadership_principles} onChange={handleChange} />
            <FI label="Стратегия роста" fk="scenario_growth_strategy" dv={f.scenario_growth_strategy} onChange={handleChange} />
            <FI label="Фокус" fk="scenario_focus" dv={f.scenario_focus} onChange={handleChange} />
          </div>
        </Sec>
      </div>{/* конец key={formKey} */}

      {saved && <div style={{ background: 'rgba(22,101,52,0.08)', border: '1px solid rgba(22,101,52,0.2)', borderRadius: 8, padding: '11px 16px', fontFamily: 'sans-serif', fontSize: 13, color: '#166534', marginBottom: 12 }}>✓ Сохранено успешно</div>}
      {error && <div style={{ background: 'rgba(153,27,27,0.08)', border: '1px solid rgba(153,27,27,0.2)', borderRadius: 8, padding: '11px 16px', fontFamily: 'sans-serif', fontSize: 13, color: '#991b1b', marginBottom: 12 }}>{error}</div>}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, paddingTop: 4, paddingBottom: 40 }}>
        <button onClick={() => save(false)} disabled={saving} style={btn({ border: '1px solid rgba(26,37,64,0.2)', background: 'transparent', color: '#1a2540' })}>{saving ? 'Сохранение…' : 'Сохранить черновик'}</button>
        <button onClick={() => save(true)} disabled={saving} style={btn({ border: 'none', background: '#1a2540', color: '#fff', fontWeight: 600 })}>{saving ? 'Сохранение…' : 'Сохранить и опубликовать'}</button>
      </div>
    </div>
  );
}
