'use client'
import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'
import {
  adminCatalog, adminContent, adminPutContent, adminWeights, adminPutWeight,
  adminHints, adminPutHint, adminItems,
  type M3AdminItem, type M3ContentKind, type M3ContentRow,
  type M3HintRow, type M3WeightRow,
} from '@/lib/m3'

/**
 * Админка Метода 3.
 *
 * Раздел открыт независимо от флага m3_enabled: тексты и калибровку заводят
 * ДО релиза, иначе их некуда класть. Доступ держит require_admin на роутере.
 *
 * Список слотов приходит из /api/admin/m3/catalog, а не зашит здесь: девять
 * ячеек матрицы, шесть линий и десять напряжений заданы методом. Копия такой
 * константы во фронте в этом проекте расходилась дважды, оба раза молча.
 *
 * Экран правит только общий слой (industry_id = null). Отраслевых
 * переопределений текстов сейчас нет ни одного, и вкладка на 18 отраслей
 * была бы формой без содержания.
 */
type Tab = 'content' | 'weights' | 'hints' | 'items'

const TABS: { id: Tab; label: string }[] = [
  { id: 'content', label: 'Тексты разбора' },
  { id: 'weights', label: 'Отраслевые веса' },
  { id: 'hints', label: 'Подсказки' },
  { id: 'items', label: 'Пункты анкеты' },
]

const ck = (kind: string, key: string) => `${kind}:${key}`

type Draft = { title: string; body: string; mistake: string; is_active: boolean }

const S: Record<string, React.CSSProperties> = {
  h1: { fontFamily: 'Georgia,serif', fontSize: 26, fontWeight: 400, margin: '0 0 6px' },
  lead: { fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)',
          lineHeight: 1.7, maxWidth: 720, margin: '0 0 8px' },
  tabs: { display: 'flex', gap: 8, flexWrap: 'wrap', margin: '18px 0 14px' },
  tab: { padding: '8px 16px', borderRadius: 999, cursor: 'pointer',
         border: '1px solid rgba(26,37,64,0.18)', background: 'none',
         fontFamily: 'sans-serif', fontSize: 13, color: '#1a2540' },
  tabOn: { background: '#c0392b', borderColor: '#c0392b', color: '#fff' },
  card: { border: '1px solid rgba(26,37,64,0.12)', borderRadius: 8,
          padding: '14px 16px', margin: '10px 0', background: '#faf9f6' },
  code: { fontFamily: 'monospace', fontSize: 13, color: '#c0392b' },
  mute: { fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)' },
  label: { fontFamily: 'sans-serif', fontSize: 11, color: 'var(--text-mute)',
           display: 'block', margin: '10px 0 4px' },
  input: { width: '100%', padding: '8px 10px', borderRadius: 6, background: '#fff',
           border: '1px solid rgba(26,37,64,0.18)', fontSize: 14,
           fontFamily: 'sans-serif' },
  area: { width: '100%', minHeight: 96, padding: '8px 10px', borderRadius: 6,
          background: '#fff', border: '1px solid rgba(26,37,64,0.18)',
          fontFamily: 'sans-serif', fontSize: 14, lineHeight: 1.6 },
  btn: { padding: '8px 16px', background: '#1a2540', color: '#fff', border: 'none',
         borderRadius: 6, fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer' },
  row: { display: 'flex', alignItems: 'center', gap: 10,
         justifyContent: 'space-between' },
  warn: { fontFamily: 'sans-serif', fontSize: 13, color: '#c0392b', margin: '8px 0' },
  ok: { fontFamily: 'sans-serif', fontSize: 13, color: '#1e3a8a', margin: '8px 0' },
}

export default function M3AdminPage() {
  const router = useRouter()
  const [ready, setReady] = useState(false)
  const [tab, setTab] = useState<Tab>('content')
  const [kinds, setKinds] = useState<M3ContentKind[]>([])
  const [kind, setKind] = useState('zone')
  const [rows, setRows] = useState<M3ContentRow[]>([])
  const [drafts, setDrafts] = useState<Record<string, Draft>>({})
  const [weights, setWeights] = useState<M3WeightRow[]>([])
  const [hints, setHints] = useState<M3HintRow[]>([])
  const [items, setItems] = useState<M3AdminItem[]>([])
  const [busy, setBusy] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [note, setNote] = useState<string | null>(null)

  useEffect(() => {
    getMe()
      .then((u: any) => {
        if (u?.role !== 'admin') { router.push('/login'); return }
        setReady(true)
      })
      .catch(() => router.push('/login'))
  }, [router])

  useEffect(() => {
    if (!ready) return
    Promise.all([adminCatalog(), adminContent()])
      .then(([c, r]) => { setKinds(c.kinds); setRows(r) })
      .catch(e => setErr(e?.message || 'Не удалось загрузить тексты'))
    adminWeights().then(setWeights).catch(() => {})
    adminHints().then(setHints).catch(() => {})
    adminItems().then(setItems).catch(() => {})
  }, [ready])

  // Общий слой: экран правит записи с industry_id = null.
  const byKey = useMemo(() => {
    const m: Record<string, M3ContentRow> = {}
    for (const r of rows) if (r.industry_id == null) m[ck(r.kind, r.key)] = r
    return m
  }, [rows])

  const active = kinds.find(k => k.kind === kind)

  function draft(k: string, key: string): Draft {
    const id = ck(k, key)
    if (drafts[id]) return drafts[id]
    const r = byKey[id]
    return {
      title: r?.title ?? '', body: r?.body ?? '',
      mistake: r?.mistake ?? '', is_active: r?.is_active ?? true,
    }
  }

  function edit(k: string, key: string, patch: Partial<Draft>) {
    setDrafts(prev => ({ ...prev, [ck(k, key)]: { ...draft(k, key), ...patch } }))
  }

  async function saveContent(k: string, key: string) {
    const d = draft(k, key)
    if (!d.title.trim() || !d.body.trim()) {
      setErr('Заголовок и текст обязательны'); return
    }
    setBusy(ck(k, key)); setErr(null); setNote(null)
    try {
      await adminPutContent({
        kind: k, key, title: d.title, body: d.body,
        mistake: k.startsWith('zone') ? (d.mistake || null) : null,
        industry_id: null, is_active: d.is_active,
      })
      setRows(await adminContent())
      setDrafts(prev => { const n = { ...prev }; delete n[ck(k, key)]; return n })
      setNote(`Сохранено: ${key}`)
    } catch (e: any) {
      setErr(e?.message || 'Не удалось сохранить')
    } finally { setBusy(null) }
  }

  async function saveWeight(w: M3WeightRow) {
    setBusy(`w${w.industry_id}`); setErr(null); setNote(null)
    try {
      await adminPutWeight(w)
      setNote(`Веса сохранены: ${w.name}`)
    } catch (e: any) {
      setErr(e?.message || 'Внутри каждой оси сумма весов должна давать 100')
    } finally { setBusy(null) }
  }

  function setW(id: number, field: keyof M3WeightRow, value: number) {
    setWeights(prev => prev.map(w => (
      w.industry_id === id ? { ...w, [field]: value } : w
    )))
  }

  async function saveHint(h: M3HintRow) {
    setBusy(h.id); setErr(null); setNote(null)
    try {
      await adminPutHint({
        industry_id: h.industry_id, item_code: h.item_code, text: h.text,
      })
      setNote(`Подсказка сохранена: ${h.item_code}`)
    } catch (e: any) {
      setErr(e?.message || 'Не удалось сохранить подсказку')
    } finally { setBusy(null) }
  }

  if (!ready) return null

  return (
    <>
      <AdminNav current="m3" />
      <div className="admin-shell">
        <AdminSide current="m3" />
        <div className="admin-main admin-main-pad" style={{ padding: '32px 40px' }}>
          <h1 style={S.h1}>Метод 3 · Матрица силы</h1>
          <p style={S.lead}>
            Разбор собирается композиционно: зона матрицы, ведущая слабая
            линия, ведущая сильная и до трёх напряжений. Одинаковая
            конфигурация линий даёт одинаковый разбор, поэтому текстов 31,
            а не 64. Незаполненный блок отчёт не роняет: он просто
            не выводится.
          </p>
          <p style={S.lead}>
            Раздел открыт независимо от флага показа Метода 3 пользователям:
            тексты заводят до релиза.
          </p>

          <div style={S.tabs}>
            {TABS.map(t => (
              <button key={t.id} type="button" onClick={() => setTab(t.id)}
                style={{ ...S.tab, ...(tab === t.id ? S.tabOn : {}) }}>
                {t.label}
              </button>
            ))}
          </div>

          {err && <p style={S.warn}>{err}</p>}
          {note && <p style={S.ok}>{note}</p>}

          {tab === 'content' && (
            <>
              <div style={S.tabs}>
                {kinds.map(k => (
                  <button key={k.kind} type="button" onClick={() => setKind(k.kind)}
                    style={{ ...S.tab, ...(kind === k.kind ? S.tabOn : {}) }}>
                    {k.kind_title} · {k.slots.length}
                  </button>
                ))}
              </div>
              {kind === 'zone_reduced' && (
                <p style={S.lead}>
                  Версия блока зоны для отчёта по одному или двум
                  направлениям. Заполняются только те зоны, где общий текст
                  ссылается на портфель: остальные откатываются к общему,
                  и переопределения им не нужны.
                </p>
              )}
              {active?.slots.map(slot => {
                const d = draft(kind, slot.key)
                const saved = byKey[ck(kind, slot.key)]
                const id = ck(kind, slot.key)
                return (
                  <div key={slot.key} style={S.card}>
                    <div style={S.row}>
                      <div>
                        <span style={S.code}>{slot.key}</span>
                        <span style={{ ...S.mute, marginLeft: 10 }}>{slot.title}</span>
                      </div>
                      <label style={S.mute}>
                        <input type="checkbox" checked={d.is_active}
                          onChange={e => edit(kind, slot.key, {
                            is_active: e.target.checked,
                          })} />
                        {' '}Активно
                      </label>
                    </div>
                    {!saved && (
                      <p style={{ ...S.mute, color: '#c0392b' }}>Не заполнено</p>
                    )}
                    <label style={S.label}>Заголовок</label>
                    <input style={S.input} value={d.title}
                      onChange={e => edit(kind, slot.key, { title: e.target.value })} />
                    <label style={S.label}>Текст</label>
                    <textarea style={S.area} value={d.body}
                      onChange={e => edit(kind, slot.key, { body: e.target.value })} />
                    {kind.startsWith('zone') && (
                      <>
                        <label style={S.label}>Типичная ошибка</label>
                        <textarea style={{ ...S.area, minHeight: 64 }} value={d.mistake}
                          onChange={e => edit(kind, slot.key, {
                            mistake: e.target.value,
                          })} />
                      </>
                    )}
                    <div style={{ marginTop: 10 }}>
                      <button type="button" style={S.btn} disabled={busy === id}
                        onClick={() => saveContent(kind, slot.key)}>
                        {busy === id ? 'Сохраняем…' : 'Сохранить'}
                      </button>
                    </div>
                  </div>
                )
              })}
            </>
          )}

          {tab === 'weights' && (
            <>
              <p style={S.lead}>
                Веса шести линий по отраслям. Внутри каждой оси сумма обязана
                давать 100: Л1+Л2+Л3 конкурентная сила, Л4+Л5+Л6
                привлекательность рынка. Правка меняет расчёт, в отличие
                от текстов. Уровень уверенности в текущих значениях низкий:
                это экспертные априорные оценки, а не эмпирика.
              </p>
              {weights.length === 0 && (
                <p style={S.mute}>Таблица весов пуста, расчёт берёт дефолты из конфига.</p>
              )}
              {weights.map(w => {
                const s = w.w_l1 + w.w_l2 + w.w_l3
                const a = w.w_l4 + w.w_l5 + w.w_l6
                const bad = s !== 100 || a !== 100
                return (
                  <div key={w.industry_id} style={S.card}>
                    <div style={S.row}>
                      <span style={S.code}>{w.industry_id} · {w.name}</span>
                      <button type="button" style={S.btn}
                        disabled={busy === `w${w.industry_id}` || bad}
                        onClick={() => saveWeight(w)}>Сохранить</button>
                    </div>
                    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 10 }}>
                      {([1, 2, 3, 4, 5, 6] as const).map(n => (
                        <label key={n} style={S.mute}>
                          Л{n}{' '}
                          <input type="number" min={0} max={100}
                            style={{ ...S.input, width: 78 }}
                            value={(w as any)[`w_l${n}`]}
                            onChange={e => setW(w.industry_id,
                              `w_l${n}` as keyof M3WeightRow, Number(e.target.value))} />
                        </label>
                      ))}
                    </div>
                    <p style={{ ...S.mute, color: bad ? '#c0392b' : undefined }}>
                      Сила {s} из 100, привлекательность {a} из 100
                    </p>
                  </div>
                )
              })}
            </>
          )}

          {tab === 'hints' && (
            <>
              <p style={S.lead}>
                Отраслевая подсказка это пример под пунктом. Текст самого
                пункта не меняется, поэтому баллы остаются сопоставимыми
                между отраслями.
              </p>
              {hints.length === 0 && <p style={S.mute}>Подсказок нет.</p>}
              {hints.map(h => (
                <div key={h.id} style={S.card}>
                  <div style={S.row}>
                    <span style={S.code}>{h.item_code} · отрасль {h.industry_id}</span>
                    <button type="button" style={S.btn} disabled={busy === h.id}
                      onClick={() => saveHint(h)}>Сохранить</button>
                  </div>
                  <textarea style={{ ...S.area, minHeight: 64 }} value={h.text}
                    onChange={e => setHints(prev => prev.map(x => (
                      x.id === h.id ? { ...x, text: e.target.value } : x
                    )))} />
                </div>
              ))}
            </>
          )}

          {tab === 'items' && (
            <>
              <p style={S.lead}>
                Пункты анкеты. Правка формулировки создаёт НОВУЮ версию,
                старая выключается и остаётся в базе: без этого выданные
                отчёты стали бы несопоставимы с новыми, а модуль динамики
                отнёс бы расхождение баллов к изменениям в бизнесе. Поэтому
                здесь список только читается, а правка идёт отдельным шагом.
              </p>
              {items.filter(i => i.is_active).map(i => (
                <div key={i.id} style={S.card}>
                  <div style={S.row}>
                    <span style={S.code}>
                      {i.code} · Л{i.line} · версия {i.item_version}
                    </span>
                    <span style={S.mute}>{i.is_reverse ? 'реверсивный' : ''}</span>
                  </div>
                  <p style={{ ...S.mute, color: '#1a2540', marginTop: 6 }}>{i.text}</p>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </>
  )
}
