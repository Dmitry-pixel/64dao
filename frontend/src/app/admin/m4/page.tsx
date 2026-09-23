'use client'
import { useEffect, useMemo, useState, type CSSProperties, type ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { getMe } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'
import {
  m4Admin,
  type M4Card, type M4CardKind, type M4Chain, type M4Construct, type M4Module,
  type M4Question, type M4Rule,
} from '@/lib/m4'

/**
 * Админка Метода 4 «Алмазное колесо».
 *
 * Правило раздела: тексты правятся свободно, логика — нет.
 *  - Коды вопросов, вариантов, правил и карточек не правятся: на них
 *    ссылаются условия правил и сохранённые ответы.
 *  - Условия срабатывания правил и структура цепочек показаны только для
 *    чтения.
 *  - Удалять нельзя, выключать можно. Вопрос, на который опирается активное
 *    правило или цепочка, сервер выключить не даст и назовёт, что мешает.
 *  - Правка формулировки поднимает версию: старые отчёты остаются
 *    сопоставимыми с новыми.
 *
 * Раздел открыт до запуска Метода 4 для клиентов: контент заводят заранее.
 */

type Tab = 'questions' | 'cards' | 'rules' | 'constructs' | 'chains'

const TABS: { id: Tab; label: string }[] = [
  { id: 'questions', label: 'Модули и вопросы' },
  { id: 'cards', label: 'Карточки отчёта' },
  { id: 'rules', label: 'Правила противоречий' },
  { id: 'constructs', label: 'Реестр конструктов' },
  { id: 'chains', label: 'Цепочки симптомов' },
]

const TYPE_LABEL: Record<string, string> = {
  bool: 'Да / Нет', scale3: 'Да / Частично / Нет', choice: 'выбор из вариантов',
  number: 'число', money: 'сумма',
}

const KIND_LABEL: Record<M4CardKind, string> = {
  module_state: 'Состояние модуля',
  module_constraint: 'Модуль — ограничение',
  recommendation: 'Рекомендации',
  dynamics: 'Динамика',
  confidence: 'Достоверность',
}

const STATE_LABEL: Record<string, string> = { low: 'низкий', mid: 'средний', high: 'высокий' }
const SEVERITY_LABEL: Record<string, string> = {
  high: 'блокирует рост', medium: 'тормозит', low: 'проявится при росте',
}
const CROSS_LABEL: Record<string, string> = {
  always: 'сверять всегда', single_direction_only: 'только при одном направлении', no: 'не сверять',
}
const UNIT_LABEL: Record<string, string> = { company: 'компания', direction: 'направление', function: 'функция' }
const METHOD_LABEL: Record<string, string> = {
  m1_base: 'Метод 1', m3: 'Метод 3', contour_finance: 'контур «Финансы»',
  contour_product: 'контур «Продукт»', contour_process: 'контур «Операции»',
  contour_market: 'контур «Рынок»', ui_bmc: 'BMC, свободный текст',
}

const lines = (s: string) => s.split('\n').map(x => x.trim()).filter(Boolean)
const errText = (e: any) => e?.message || 'Не удалось сохранить'

export default function M4AdminPage() {
  const router = useRouter()
  const [ready, setReady] = useState(false)
  const [tab, setTab] = useState<Tab>('questions')
  const [modules, setModules] = useState<M4Module[]>([])
  const [questions, setQuestions] = useState<M4Question[]>([])
  const [cards, setCards] = useState<M4Card[]>([])
  const [rules, setRules] = useState<M4Rule[]>([])
  const [constructs, setConstructs] = useState<M4Construct[]>([])
  const [chains, setChains] = useState<M4Chain[]>([])
  const [loadErr, setLoadErr] = useState<string | null>(null)

  useEffect(() => {
    getMe()
      .then((u: any) => { if (u?.role !== 'admin') router.push('/login'); else setReady(true) })
      .catch(() => router.push('/login'))
  }, [router])

  useEffect(() => {
    if (!ready) return
    Promise.all([
      m4Admin.modules(), m4Admin.questions(), m4Admin.cards(),
      m4Admin.rules(), m4Admin.constructs(), m4Admin.chains(),
    ])
      .then(([m, q, c, r, k, ch]) => {
        setModules(m); setQuestions(q); setCards(c); setRules(r); setConstructs(k); setChains(ch)
      })
      .catch(e => setLoadErr(e?.message || 'Не удалось загрузить контент Метода 4'))
  }, [ready])

  const moduleName = useMemo(() => {
    const m: Record<number, string> = {}
    for (const x of modules) m[x.code] = x.name
    return m
  }, [modules])

  if (!ready) return null

  const replace = <T,>(list: T[], key: keyof T, row: T) =>
    list.map(x => (x[key] === row[key] ? row : x))

  return (
    <>
      <AdminNav current="m4" />
      <div className="admin-shell">
        <AdminSide current="m4" />
        <div className="admin-main admin-main-pad" style={{ padding: '32px 40px' }}>
          <span className="label-red">Контент метода</span>
          <h1 style={S.h1}>Метод 4 · Алмазное колесо</h1>
          <p style={S.lead}>
            Тексты вопросов, вариантов ответа, карточек отчёта, правил и цепочек правятся здесь,
            без выпуска новой версии сайта. Коды и условия срабатывания правил не правятся: на них
            ссылаются расчёт и сохранённые ответы. Удалять нельзя, выключать можно.
          </p>
          <p style={S.lead}>
            Правка формулировки вопроса или карточки поднимает её версию. Уже выданные отчёты
            хранят свою версию и не меняются задним числом.
          </p>

          <div style={S.tabs}>
            {TABS.map(t => (
              <button key={t.id} type="button" onClick={() => setTab(t.id)}
                style={{ ...S.tab, ...(tab === t.id ? S.tabOn : {}) }}>
                {t.label}
              </button>
            ))}
          </div>

          {loadErr && <p style={S.warn}>{loadErr}</p>}

          {tab === 'questions' && (
            <QuestionsTab modules={modules} questions={questions}
              onModule={m => setModules(replace(modules, 'code', m))}
              onQuestion={q => setQuestions(replace(questions, 'code', q))} />
          )}
          {tab === 'cards' && (
            <CardsTab cards={cards} moduleName={moduleName}
              onCard={c => setCards(replace(cards, 'id', c))} />
          )}
          {tab === 'rules' && (
            <>
              <p style={S.lead}>
                Правило срабатывает, когда два управленческих решения компании мешают друг другу.
                Тексты правятся; условие срабатывания показано для справки. Выключенное правило в
                отчёт не попадает.
              </p>
              {rules.map(r => <RuleEditor key={r.code} rule={r}
                onSaved={x => setRules(replace(rules, 'code', x))} />)}
            </>
          )}
          {tab === 'constructs' && (
            <>
              <p style={S.lead}>
                Конструкт — то, что метод пытается узнать, независимо от формулировки вопроса.
                По нему сверяются ответы Метода 3 и Метода 4 и не задаётся один вопрос дважды.
                Связи с пунктами других методов показаны для справки.
              </p>
              {constructs.map(c => <ConstructEditor key={c.code} c={c}
                onSaved={x => setConstructs(replace(constructs, 'code', x))} />)}
            </>
          )}
          {tab === 'chains' && (
            <>
              <p style={S.lead}>
                Цепочка ведёт от симптома, который видит собственник, к модулю-причине и первому
                действию. Тексты правятся; по каким вопросам распознаётся симптом — показано для
                справки.
              </p>
              {chains.map(c => <ChainEditor key={c.code} c={c} moduleName={moduleName}
                onSaved={x => setChains(replace(chains, 'code', x))} />)}
            </>
          )}
        </div>
      </div>
    </>
  )
}

// ── Общие элементы ───────────────────────────────────────────────────────────

function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <div>
      <label style={S.label}>{label}</label>
      {children}
      {hint && <p style={{ ...S.mute, margin: '4px 0 0' }}>{hint}</p>}
    </div>
  )
}

function SaveBar({ busy, dirty, onSave, msg, err, extra }: {
  busy: boolean; dirty: boolean; onSave: () => void; msg: string | null; err: string | null; extra?: ReactNode
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 12, flexWrap: 'wrap' }}>
      <button type="button" style={{ ...S.btn, opacity: dirty ? 1 : 0.45 }}
        disabled={busy || !dirty} onClick={onSave}>
        {busy ? 'Сохраняем…' : 'Сохранить'}
      </button>
      {extra}
      {err && <span style={{ ...S.warn, margin: 0 }}>{err}</span>}
      {msg && !err && <span style={{ ...S.ok, margin: 0 }}>{msg}</span>}
    </div>
  )
}

function useSave() {
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const run = async (fn: () => Promise<void>, ok = 'Сохранено') => {
    setBusy(true); setErr(null); setMsg(null)
    try { await fn(); setMsg(ok) } catch (e) { setErr(errText(e)) } finally { setBusy(false) }
  }
  return { busy, msg, err, run }
}

function diff<T extends object>(orig: T, draft: T, keys: (keyof T)[]): Partial<T> {
  const out: Partial<T> = {}
  for (const k of keys) {
    if (JSON.stringify(orig[k]) !== JSON.stringify(draft[k])) out[k] = draft[k]
  }
  return out
}

const numOrNull = (s: string) => (s.trim() === '' ? null : Number(s))

// ── Модули и вопросы ─────────────────────────────────────────────────────────

function QuestionsTab({ modules, questions, onModule, onQuestion }: {
  modules: M4Module[]; questions: M4Question[]
  onModule: (m: M4Module) => void; onQuestion: (q: M4Question) => void
}) {
  const [code, setCode] = useState(1)
  const mod = modules.find(m => m.code === code)
  const list = questions.filter(q => q.module_code === code)
  const active = list.filter(q => q.is_active).length

  return (
    <>
      <div style={S.tabs}>
        {modules.map(m => (
          <button key={m.code} type="button" onClick={() => setCode(m.code)}
            style={{ ...S.chip, ...(code === m.code ? S.chipOn : {}) }}>
            {m.code}. {m.name}
          </button>
        ))}
      </div>
      {mod && <ModuleEditor key={mod.code} m={mod} onSaved={onModule} />}
      <p style={{ ...S.mute, margin: '18px 0 6px' }}>
        Вопросов в модуле: {list.length}, включено: {active}. «Экспресс» — вопрос входит в
        бесплатную экспресс-диагностику из 20 вопросов.
      </p>
      {list.map(q => <QuestionEditor key={q.code} q={q} onSaved={onQuestion} />)}
    </>
  )
}

function ModuleEditor({ m, onSaved }: { m: M4Module; onSaved: (m: M4Module) => void }) {
  const [d, setD] = useState(m)
  const s = useSave()
  const keys: (keyof M4Module)[] = ['name', 'client_question', 'why_it_matters', 'intro']
  const patch = diff(m, d, keys)
  return (
    <div style={{ ...S.card, background: '#f3f0e8' }}>
      <div style={S.row}>
        <span style={S.code}>Модуль {m.code}{m.is_effect ? ' · следствие остальных девяти' : ''}</span>
      </div>
      <Field label="Название модуля">
        <input style={S.input} value={d.name} onChange={e => setD({ ...d, name: e.target.value })} />
      </Field>
      <Field label="Вопрос клиента, на который отвечает модуль">
        <input style={S.input} value={d.client_question}
          onChange={e => setD({ ...d, client_question: e.target.value })} />
      </Field>
      <Field label="Почему это важно">
        <textarea style={{ ...S.area, minHeight: 64 }} value={d.why_it_matters}
          onChange={e => setD({ ...d, why_it_matters: e.target.value })} />
      </Field>
      <Field label="Вводный абзац перед вопросами модуля">
        <textarea style={{ ...S.area, minHeight: 64 }} value={d.intro ?? ''}
          onChange={e => setD({ ...d, intro: e.target.value || null })} />
      </Field>
      <SaveBar busy={s.busy} dirty={Object.keys(patch).length > 0} msg={s.msg} err={s.err}
        onSave={() => s.run(async () => { const x = await m4Admin.putModule(m.code, patch); onSaved(x); setD(x) })} />
    </div>
  )
}

function QuestionEditor({ q, onSaved }: { q: M4Question; onSaved: (q: M4Question) => void }) {
  const [d, setD] = useState(q)
  const [opts, setOpts] = useState(q.options)
  const s = useSave()
  const keys: (keyof M4Question)[] = [
    'text', 'weight', 'tier', 'unit', 'min_value', 'max_value', 'note_internal',
    'reverse', 'unknown_allowed', 'unknown_score', 'unknown_confidence_penalty',
  ]
  const patch = diff(q, d, keys)
  const optChanged = opts.filter(o => {
    const was = q.options.find(x => x.value === o.value)
    return was && (was.label !== o.label || was.score !== o.score)
  })
  const dirty = Object.keys(patch).length > 0 || optChanged.length > 0
  const numeric = q.type === 'number' || q.type === 'money'

  const save = () => s.run(async () => {
    let x = q
    if (Object.keys(patch).length) x = await m4Admin.putQuestion(q.code, patch)
    for (const o of optChanged) x = await m4Admin.putOption(q.code, o.value, { label: o.label, score: o.score })
    onSaved(x); setD(x); setOpts(x.options)
  }, 'Сохранено')

  const toggle = () => s.run(async () => {
    const x = await m4Admin.setQuestionActive(q.code, !q.is_active)
    onSaved(x); setD(x); setOpts(x.options)
  }, q.is_active ? 'Вопрос выключен' : 'Вопрос включён')

  const facts = [
    q.construct_code && `конструкт: ${q.construct_code}`,
    q.control_pair && `контрольная пара: ${q.control_pair}`,
    q.applies_when && `показывается, если: ${Object.entries(q.applies_when).map(([k, v]) => `${k} = ${v.join(' / ')}`).join('; ')}`,
    q.metric_code && `метрика: ${q.metric_code}`,
    q.affects === 'prioritization' && 'в балл не идёт — влияет на очередь действий',
    q.score_neutral && 'в балл не идёт — служебный вопрос',
  ].filter(Boolean) as string[]

  return (
    <div style={{ ...S.card, opacity: q.is_active ? 1 : 0.6 }}>
      <div style={S.row}>
        <div>
          <span style={S.code}>{q.code}</span>
          <span style={{ ...S.mute, marginLeft: 10 }}>
            {TYPE_LABEL[q.type]} · версия {q.item_version}{q.is_fact ? ' · факт' : ''}
          </span>
        </div>
        <span style={{ ...S.badge, ...(q.is_active ? {} : S.badgeOff) }}>
          {q.is_active ? 'включён' : 'выключен'}
        </span>
      </div>

      <Field label="Формулировка">
        <textarea style={{ ...S.area, minHeight: 56 }} value={d.text}
          onChange={e => setD({ ...d, text: e.target.value })} />
      </Field>

      <div style={S.grid}>
        <Field label="Вес в балле модуля">
          <select style={S.input} value={d.weight} onChange={e => setD({ ...d, weight: Number(e.target.value) })}>
            <option value={1}>1 — обычный</option><option value={2}>2 — важный</option>
            <option value={3}>3 — ключевой</option>
          </select>
        </Field>
        <Field label="Где задаётся">
          <select style={S.input} value={d.tier} onChange={e => setD({ ...d, tier: e.target.value as 'u0' | 'u1' })}>
            <option value="u0">экспресс и полная</option><option value="u1">только полная</option>
          </select>
        </Field>
        {numeric && (
          <>
            <Field label="Единица">
              <input style={S.input} value={d.unit ?? ''} onChange={e => setD({ ...d, unit: e.target.value || null })} />
            </Field>
            <Field label="Минимум">
              <input style={S.input} value={d.min_value ?? ''} onChange={e => setD({ ...d, min_value: numOrNull(e.target.value) })} />
            </Field>
            <Field label="Максимум">
              <input style={S.input} value={d.max_value ?? ''} onChange={e => setD({ ...d, max_value: numOrNull(e.target.value) })} />
            </Field>
          </>
        )}
      </div>

      {opts.length > 0 && (
        <Field label="Варианты ответа: подпись и балл (0–100)"
          hint={q.score_neutral || q.affects
            ? 'Этот вопрос в балл модуля не идёт: баллы вариантов не используются, важны подписи и сам ответ.'
            : undefined}>
          {opts.map(o => (
            <div key={o.value} style={{ display: 'flex', gap: 8, marginBottom: 6, alignItems: 'center' }}>
              <input style={{ ...S.input, flex: 1 }} value={o.label}
                onChange={e => setOpts(opts.map(x => (x.value === o.value ? { ...x, label: e.target.value } : x)))} />
              <input style={{ ...S.input, width: 80 }} type="number" min={0} max={100} value={o.score ?? ''}
                onChange={e => setOpts(opts.map(x => (x.value === o.value ? { ...x, score: numOrNull(e.target.value) } : x)))} />
            </div>
          ))}
        </Field>
      )}

      <details style={{ marginTop: 10 }}>
        <summary style={{ ...S.mute, cursor: 'pointer' }}>Поведение ответа и служебное</summary>
        <p style={{ ...S.warn, fontSize: 12 }}>
          Эти поля меняют расчёт балла, а не текст. Меняйте осознанно: версия вопроса поднимется.
        </p>
        <label style={S.check}>
          <input type="checkbox" checked={d.reverse} onChange={e => setD({ ...d, reverse: e.target.checked })} />
          Обратный вопрос: ответ «Да» — это плохо
        </label>
        <label style={S.check}>
          <input type="checkbox" checked={d.unknown_allowed}
            onChange={e => setD({ ...d, unknown_allowed: e.target.checked, unknown_score: e.target.checked ? d.unknown_score : null })} />
          Показывать вариант «Не знаю»
        </label>
        {d.unknown_allowed && !q.affects && (
          <div style={S.grid}>
            <Field label="Балл за «Не знаю»" hint="Пусто — в балл не идёт, только снижает достоверность. 0 — незнание само является плохим ответом.">
              <input style={S.input} value={d.unknown_score ?? ''}
                onChange={e => setD({ ...d, unknown_score: numOrNull(e.target.value) })} />
            </Field>
            <Field label="Снижение достоверности за «Не знаю»">
              <select style={S.input} value={d.unknown_confidence_penalty}
                onChange={e => setD({ ...d, unknown_confidence_penalty: Number(e.target.value) })}>
                {[0, 1, 2, 3].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </Field>
          </div>
        )}
        <Field label="Заметка для администратора (клиент её не видит)">
          <textarea style={{ ...S.area, minHeight: 48 }} value={d.note_internal ?? ''}
            onChange={e => setD({ ...d, note_internal: e.target.value || null })} />
        </Field>
        {facts.length > 0 && <p style={S.mute}>{facts.join(' · ')}</p>}
        {q.source_ref && <p style={S.mute}>Источник (только для администратора): {q.source_ref}</p>}
      </details>

      <SaveBar busy={s.busy} dirty={dirty} msg={s.msg} err={s.err} onSave={save}
        extra={<button type="button" style={S.btnGhost} disabled={s.busy} onClick={toggle}>
          {q.is_active ? 'Выключить' : 'Включить'}
        </button>} />
    </div>
  )
}

// ── Карточки ─────────────────────────────────────────────────────────────────

function CardsTab({ cards, moduleName, onCard }: {
  cards: M4Card[]; moduleName: Record<number, string>; onCard: (c: M4Card) => void
}) {
  const kinds = Object.keys(KIND_LABEL) as M4CardKind[]
  const [kind, setKind] = useState<M4CardKind>('module_state')
  const list = cards.filter(c => c.kind === kind)
  return (
    <>
      <div style={S.tabs}>
        {kinds.map(k => (
          <button key={k} type="button" onClick={() => setKind(k)}
            style={{ ...S.chip, ...(kind === k ? S.chipOn : {}) }}>
            {KIND_LABEL[k]} · {cards.filter(c => c.kind === k).length}
          </button>
        ))}
      </div>
      {kind === 'recommendation' && (
        <p style={S.lead}>
          Эффект, срок и затраты — входы очереди действий: приоритет = эффект × 12 / недели ÷
          (затраты × сопротивление). Без них рекомендацию нельзя поставить в очередь.
        </p>
      )}
      {list.map(c => <CardEditor key={c.id} c={c} moduleName={moduleName} onSaved={onCard} />)}
    </>
  )
}

function CardEditor({ c, moduleName, onSaved }: {
  c: M4Card; moduleName: Record<number, string>; onSaved: (c: M4Card) => void
}) {
  const [d, setD] = useState(c)
  const [steps, setSteps] = useState((c.steps ?? []).join('\n'))
  const s = useSave()
  const keys: (keyof M4Card)[] = ['title', 'body', 'mistake', 'first_step', 'how_to_check',
    'effect', 'speed_weeks', 'cost', 'is_active']
  const patch: Partial<M4Card> = diff(c, d, keys)
  const newSteps = lines(steps)
  if (JSON.stringify(newSteps) !== JSON.stringify(c.steps ?? [])) patch.steps = newSteps
  const reco = c.kind === 'recommendation'
  const where = [
    c.module_code && `модуль ${c.module_code}. ${moduleName[c.module_code] ?? ''}`,
    c.state && `уровень: ${STATE_LABEL[c.state]}`,
    c.rule_code && `правило ${c.rule_code}`,
  ].filter(Boolean).join(' · ')

  return (
    <div style={{ ...S.card, opacity: d.is_active ? 1 : 0.6 }}>
      <div style={S.row}>
        <div>
          <span style={S.code}>{c.key}</span>
          <span style={{ ...S.mute, marginLeft: 10 }}>{where}{where ? ' · ' : ''}версия {c.item_version}</span>
        </div>
        <label style={S.check}>
          <input type="checkbox" checked={d.is_active} onChange={e => setD({ ...d, is_active: e.target.checked })} />
          Включена
        </label>
      </div>
      <Field label="Заголовок">
        <input style={S.input} value={d.title} onChange={e => setD({ ...d, title: e.target.value })} />
      </Field>
      <Field label="Текст">
        <textarea style={S.area} value={d.body} onChange={e => setD({ ...d, body: e.target.value })} />
      </Field>
      {(c.mistake !== null || !reco) && (
        <Field label="Типичная ошибка">
          <textarea style={{ ...S.area, minHeight: 56 }} value={d.mistake ?? ''}
            onChange={e => setD({ ...d, mistake: e.target.value || null })} />
        </Field>
      )}
      {reco && (
        <>
          <Field label="Шаги — по одному в строке">
            <textarea style={{ ...S.area, minHeight: 72 }} value={steps} onChange={e => setSteps(e.target.value)} />
          </Field>
          <Field label="Первый шаг на этой неделе">
            <input style={S.input} value={d.first_step ?? ''} onChange={e => setD({ ...d, first_step: e.target.value || null })} />
          </Field>
          <Field label="Как проверить, что сработало">
            <input style={S.input} value={d.how_to_check ?? ''} onChange={e => setD({ ...d, how_to_check: e.target.value || null })} />
          </Field>
          <div style={S.grid}>
            <Field label="Эффект (1–3)">
              <select style={S.input} value={d.effect ?? 1} onChange={e => setD({ ...d, effect: Number(e.target.value) })}>
                {[1, 2, 3].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </Field>
            <Field label="Недель до результата">
              <input style={S.input} type="number" min={1} max={104} value={d.speed_weeks ?? ''}
                onChange={e => setD({ ...d, speed_weeks: numOrNull(e.target.value) })} />
            </Field>
            <Field label="Затраты (1–3)">
              <select style={S.input} value={d.cost ?? 1} onChange={e => setD({ ...d, cost: Number(e.target.value) })}>
                {[1, 2, 3].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </Field>
          </div>
        </>
      )}
      <SaveBar busy={s.busy} dirty={Object.keys(patch).length > 0} msg={s.msg} err={s.err}
        onSave={() => s.run(async () => {
          const x = await m4Admin.putCard(c.id, patch); onSaved(x); setD(x); setSteps((x.steps ?? []).join('\n'))
        })} />
    </div>
  )
}

// ── Правила ──────────────────────────────────────────────────────────────────

function RuleEditor({ rule, onSaved }: { rule: M4Rule; onSaved: (r: M4Rule) => void }) {
  const [d, setD] = useState(rule)
  const [fixes, setFixes] = useState(rule.fix_one_of.join('\n'))
  const s = useSave()
  const patch: Partial<M4Rule> = diff(rule, d, ['title', 'severity', 'diagnosis', 'what_happens',
    'cost_of_inaction', 'is_active'])
  if (JSON.stringify(lines(fixes)) !== JSON.stringify(rule.fix_one_of)) patch.fix_one_of = lines(fixes)
  return (
    <div style={{ ...S.card, opacity: d.is_active ? 1 : 0.6 }}>
      <div style={S.row}>
        <div>
          <span style={S.code}>{rule.code}</span>
          {rule.is_mvp && <span style={{ ...S.badge, marginLeft: 10 }}>в первой версии</span>}
        </div>
        <label style={S.check}>
          <input type="checkbox" checked={d.is_active} onChange={e => setD({ ...d, is_active: e.target.checked })} />
          Включено
        </label>
      </div>
      <div style={S.grid}>
        <Field label="Название">
          <input style={S.input} value={d.title} onChange={e => setD({ ...d, title: e.target.value })} />
        </Field>
        <Field label="Серьёзность">
          <select style={S.input} value={d.severity} onChange={e => setD({ ...d, severity: e.target.value as M4Rule['severity'] })}>
            {Object.entries(SEVERITY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </Field>
      </div>
      <Field label="Диагноз: какие два решения мешают друг другу">
        <textarea style={S.area} value={d.diagnosis} onChange={e => setD({ ...d, diagnosis: e.target.value })} />
      </Field>
      <Field label="Что происходит в компании">
        <textarea style={{ ...S.area, minHeight: 64 }} value={d.what_happens} onChange={e => setD({ ...d, what_happens: e.target.value })} />
      </Field>
      <Field label="Варианты решения — по одному в строке">
        <textarea style={{ ...S.area, minHeight: 64 }} value={fixes} onChange={e => setFixes(e.target.value)} />
      </Field>
      <Field label="Цена бездействия">
        <textarea style={{ ...S.area, minHeight: 48 }} value={d.cost_of_inaction} onChange={e => setD({ ...d, cost_of_inaction: e.target.value })} />
      </Field>
      <details style={{ marginTop: 8 }}>
        <summary style={{ ...S.mute, cursor: 'pointer' }}>Условие срабатывания (только чтение)</summary>
        <pre style={S.pre}>{JSON.stringify(rule.conditions, null, 2)}</pre>
        {rule.source_ref && <p style={S.mute}>Источник (только для администратора): {rule.source_ref}</p>}
      </details>
      <SaveBar busy={s.busy} dirty={Object.keys(patch).length > 0} msg={s.msg} err={s.err}
        onSave={() => s.run(async () => {
          const x = await m4Admin.putRule(rule.code, patch); onSaved(x); setD(x); setFixes(x.fix_one_of.join('\n'))
        })} />
    </div>
  )
}

// ── Конструкты ───────────────────────────────────────────────────────────────

function ConstructEditor({ c, onSaved }: { c: M4Construct; onSaved: (c: M4Construct) => void }) {
  const [d, setD] = useState(c)
  const s = useSave()
  const patch = diff(c, d, ['name', 'reusable', 'cross_check', 'cross_check_why', 'note', 'is_active'])
  return (
    <div style={{ ...S.card, opacity: d.is_active ? 1 : 0.6 }}>
      <div style={S.row}>
        <span style={S.code}>{c.code} · уровень: {UNIT_LABEL[c.unit]}</span>
        <label style={S.check}>
          <input type="checkbox" checked={d.is_active} onChange={e => setD({ ...d, is_active: e.target.checked })} />
          Включён
        </label>
      </div>
      <Field label="Что узнаём">
        <input style={S.input} value={d.name} onChange={e => setD({ ...d, name: e.target.value })} />
      </Field>
      <div style={S.grid}>
        <Field label="Сверка ответов Методов 3 и 4">
          <select style={S.input} value={d.cross_check ?? ''}
            onChange={e => setD({ ...d, cross_check: (e.target.value || null) as M4Construct['cross_check'] })}>
            <option value="">не задана</option>
            {Object.entries(CROSS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </Field>
        <label style={{ ...S.check, marginTop: 28 }}>
          <input type="checkbox" checked={d.reusable} onChange={e => setD({ ...d, reusable: e.target.checked })} />
          Ответ можно переиспользовать
        </label>
      </div>
      <Field label="Почему сверка корректна или нет">
        <textarea style={{ ...S.area, minHeight: 48 }} value={d.cross_check_why ?? ''}
          onChange={e => setD({ ...d, cross_check_why: e.target.value || null })} />
      </Field>
      <Field label="Заметка">
        <textarea style={{ ...S.area, minHeight: 48 }} value={d.note ?? ''}
          onChange={e => setD({ ...d, note: e.target.value || null })} />
      </Field>
      {c.links.length > 0 && (
        <p style={S.mute}>
          Связи: {c.links.map(l => `${METHOD_LABEL[l.method] ?? l.method} ${l.item_code}${l.reverse ? ' (обратный)' : ''}${l.dynamic ? ' (динамика)' : ''}`).join(' · ')}
        </p>
      )}
      <SaveBar busy={s.busy} dirty={Object.keys(patch).length > 0} msg={s.msg} err={s.err}
        onSave={() => s.run(async () => { const x = await m4Admin.putConstruct(c.code, patch); onSaved(x); setD(x) })} />
    </div>
  )
}

// ── Цепочки ──────────────────────────────────────────────────────────────────

function ChainEditor({ c, moduleName, onSaved }: {
  c: M4Chain; moduleName: Record<number, string>; onSaved: (c: M4Chain) => void
}) {
  const [d, setD] = useState(c)
  const [chain, setChain] = useState(c.chain.join('\n'))
  const s = useSave()
  const patch: Partial<M4Chain> = diff(c, d, ['label', 'first_action', 'note', 'is_active'])
  if (JSON.stringify(lines(chain)) !== JSON.stringify(c.chain)) patch.chain = lines(chain)
  return (
    <div style={{ ...S.card, opacity: d.is_active ? 1 : 0.6 }}>
      <div style={S.row}>
        <span style={S.code}>{c.code}</span>
        <label style={S.check}>
          <input type="checkbox" checked={d.is_active} onChange={e => setD({ ...d, is_active: e.target.checked })} />
          Включена
        </label>
      </div>
      <Field label="Симптом, как его видит собственник">
        <input style={S.input} value={d.label} onChange={e => setD({ ...d, label: e.target.value })} />
      </Field>
      <Field label="Цепочка причин — по одному звену в строке">
        <textarea style={S.area} value={chain} onChange={e => setChain(e.target.value)} />
      </Field>
      <Field label="Первое действие">
        <textarea style={{ ...S.area, minHeight: 48 }} value={d.first_action} onChange={e => setD({ ...d, first_action: e.target.value })} />
      </Field>
      <Field label="Заметка">
        <textarea style={{ ...S.area, minHeight: 40 }} value={d.note ?? ''} onChange={e => setD({ ...d, note: e.target.value || null })} />
      </Field>
      <p style={S.mute}>
        Распознаётся по: {c.detected_by.join(', ')} · модули-причины: {c.root_modules.map(m => `${m}. ${moduleName[m] ?? ''}`).join(', ')} ·
        проверочные вопросы: {c.check_questions.join(', ')}
      </p>
      <SaveBar busy={s.busy} dirty={Object.keys(patch).length > 0} msg={s.msg} err={s.err}
        onSave={() => s.run(async () => {
          const x = await m4Admin.putChain(c.code, patch); onSaved(x); setD(x); setChain(x.chain.join('\n'))
        })} />
    </div>
  )
}

const S: Record<string, CSSProperties> = {
  h1: { fontFamily: 'Georgia,serif', fontSize: 26, fontWeight: 400, margin: '6px 0 6px' },
  lead: { fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', lineHeight: 1.7, maxWidth: 760, margin: '0 0 8px' },
  tabs: { display: 'flex', gap: 8, flexWrap: 'wrap', margin: '18px 0 14px' },
  tab: { padding: '8px 16px', borderRadius: 999, cursor: 'pointer', border: '1px solid rgba(26,37,64,0.18)',
    background: 'none', fontFamily: 'sans-serif', fontSize: 13, color: '#1a2540' },
  tabOn: { background: '#c0392b', borderColor: '#c0392b', color: '#fff' },
  chip: { padding: '6px 12px', borderRadius: 6, cursor: 'pointer', border: '1px solid rgba(26,37,64,0.15)',
    background: 'rgba(255,255,255,0.6)', fontFamily: 'sans-serif', fontSize: 12, color: '#1a2540' },
  chipOn: { background: '#1a2540', borderColor: '#1a2540', color: '#fff' },
  card: { border: '1px solid rgba(26,37,64,0.12)', borderRadius: 8, padding: '14px 16px', margin: '10px 0', background: '#faf9f6' },
  code: { fontFamily: 'monospace', fontSize: 13, color: '#c0392b' },
  mute: { fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)', lineHeight: 1.6 },
  label: { fontFamily: 'sans-serif', fontSize: 11, color: 'var(--text-mute)', display: 'block', margin: '10px 0 4px' },
  input: { width: '100%', padding: '8px 10px', borderRadius: 6, background: '#fff',
    border: '1px solid rgba(26,37,64,0.18)', fontSize: 14, fontFamily: 'sans-serif', boxSizing: 'border-box' },
  area: { width: '100%', minHeight: 96, padding: '8px 10px', borderRadius: 6, background: '#fff',
    border: '1px solid rgba(26,37,64,0.18)', fontFamily: 'sans-serif', fontSize: 14, lineHeight: 1.6, boxSizing: 'border-box' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 },
  btn: { padding: '8px 16px', background: '#1a2540', color: '#fff', border: 'none', borderRadius: 6,
    fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer' },
  btnGhost: { padding: '8px 16px', background: 'none', color: '#1a2540', border: '1px solid rgba(26,37,64,0.25)',
    borderRadius: 6, fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer' },
  row: { display: 'flex', alignItems: 'center', gap: 10, justifyContent: 'space-between', flexWrap: 'wrap' },
  check: { fontFamily: 'sans-serif', fontSize: 13, color: '#1a2540', display: 'flex', alignItems: 'center', gap: 6, margin: '6px 0' },
  badge: { fontFamily: 'sans-serif', fontSize: 11, padding: '2px 8px', borderRadius: 10, background: '#dcfce7', color: '#166534' },
  badgeOff: { background: '#f1f5f9', color: '#475569' },
  pre: { fontFamily: 'monospace', fontSize: 12, background: '#fff', border: '1px solid rgba(26,37,64,0.12)',
    borderRadius: 6, padding: 10, overflowX: 'auto' },
  warn: { fontFamily: 'sans-serif', fontSize: 13, color: '#c0392b', margin: '8px 0' },
  ok: { fontFamily: 'sans-serif', fontSize: 13, color: '#1e3a8a', margin: '8px 0' },
}
