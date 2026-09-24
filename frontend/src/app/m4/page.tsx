'use client'

// force-dynamic + Suspense: useSearchParams иначе не даёт странице
// пререндериться статически (Next 14 App Router).
export const dynamic = 'force-dynamic'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { m4, type M4ClientOption, type M4Mode, type M4Profile, type M4RunOut } from '@/lib/m4'
import { M4 } from '@/components/m4/styles'

const STATUS_LABEL: Record<string, string> = {
  draft: 'анкета заполняется',
  filled: 'анкета заполнена',
  calculated: 'рассчитана',
}
const MODE_LABEL: Record<M4Mode, string> = { express: 'Экспресс', full: 'Полная' }

type Phase = 'loading' | 'list' | 'setup'

function M4PageInner() {
  const router = useRouter()
  const sp = useSearchParams()
  // Название компании приходит из /assessment, как у Метода 3: второй
  // формы ввода названия быть не должно, поле ниже только предзаполнено.
  const companyParam = sp.get('company') || ''

  const [phase, setPhase] = useState<Phase>('loading')
  const [runs, setRuns] = useState<M4RunOut[]>([])
  const [revenueOptions, setRevenueOptions] = useState<M4ClientOption[]>([])
  const [fullLeft, setFullLeft] = useState<number | null>(null)
  const [expressLeft, setExpressLeft] = useState<number | null>(null)
  const [followup, setFollowup] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [companyName, setCompanyName] = useState(companyParam)
  const [revenueModel, setRevenueModel] = useState<M4Profile['revenue_model'] | ''>('')
  const [mode, setMode] = useState<M4Mode>(sp.get('mode') === 'full' ? 'full' : 'express')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([m4.runs(), m4.questionnaire('express'), m4.credits()])
      .then(([rs, q, cr]) => {
        setRuns(rs)
        setRevenueOptions(q.profile_options.revenue_model ?? [])
        setFullLeft(cr.full_available)
        setExpressLeft(cr.express_available)
        // Экспресс уже израсходован — по умолчанию предлагаем полную.
        if (cr.express_available === 0) setMode('full')
        setPhase(companyParam || !rs.length ? 'setup' : 'list')
      })
      .catch((e: any) => setLoadError(
        e?.status === 404 ? 'Раздел пока недоступен.' : e?.message || 'Не удалось загрузить данные.',
      ))
  }, [companyParam])

  // Повтор полной диагностики зависит от компании: спрашиваем сервер по
  // названию, с задержкой, чтобы не бить по API на каждый символ.
  useEffect(() => {
    const name = companyName.trim()
    if (!name) { setFollowup(false); return }
    const t = setTimeout(() => {
      m4.credits(name).then(cr => setFollowup(cr.followup_available)).catch(() => setFollowup(false))
    }, 400)
    return () => clearTimeout(t)
  }, [companyName])

  // Начатый экспресс этой компании продолжается и после исчерпания лимита.
  const expressDraft = runs.some(r => r.mode === 'express' && r.status !== 'calculated'
    && (r.company_name ?? '').trim() === companyName.trim())
  const expressBlocked = expressLeft !== null && expressLeft <= 0 && !expressDraft
  const fullBlocked = fullLeft !== null && fullLeft <= 0 && !followup

  async function start() {
    const name = companyName.trim()
    if (!name) { setError('Укажите название компании.'); return }
    if (mode === 'full' && !revenueModel) { setError('Выберите, как устроена оплата у компании.'); return }
    setBusy(true)
    setError(null)
    try {
      const run = await m4.createRun({
        mode,
        company_name: name,
        profile: revenueModel ? { revenue_model: revenueModel } : undefined,
      })
      router.push(`/m4/${run.id}`)
    } catch (e: any) {
      setError(typeof e?.message === 'string' ? e.message : 'Не удалось начать диагностику.')
      setBusy(false)
    }
  }

  if (loadError) return (
    <div style={M4.page}><div style={M4.stage}>
      <p style={M4.warn}>{loadError}</p>
      <button style={M4.btnGhost} onClick={() => router.push('/dashboard')}>← В кабинет</button>
    </div></div>
  )

  if (phase === 'loading') return (
    <div style={M4.page}><div style={M4.stage}><p style={M4.muted}>Загрузка…</p></div></div>
  )

  if (phase === 'list') return (
    <div style={M4.page}><div style={M4.stage}>
      <span style={M4.label}>Метод 04 · Алмазное колесо</span>
      <h1 style={M4.h1}>Ваши диагностики</h1>
      <p style={M4.text}>
        Десять управленческих модулей компании: где разрыв, какой из них сдерживает
        остальные и с чего начинать.
      </p>

      {runs.map(r => (
        <div key={r.id} style={M4.listRow}>
          <span>
            {r.company_name || 'Без названия'} · {MODE_LABEL[r.mode]}{r.is_followup && ' · повтор'}
            {r.status !== 'calculated' && ` · ${r.progress.answered} из ${r.progress.required}`}
          </span>
          <span style={M4.status}>{STATUS_LABEL[r.status] ?? r.status}</span>
          <button
            style={M4.btnGhost}
            onClick={() => router.push(r.status === 'calculated' ? `/m4/${r.id}/result` : `/m4/${r.id}`)}
          >
            {r.status === 'calculated' ? 'Результат' : 'Продолжить'} →
          </button>
        </div>
      ))}

      <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
        <button style={M4.btnGhost} onClick={() => router.push('/dashboard')}>← В кабинет</button>
        <button style={M4.btnPrimary} onClick={() => setPhase('setup')}>Новая диагностика →</button>
      </div>
    </div></div>
  )

  return (
    <div style={M4.page}><div style={M4.stage}>
      <span style={M4.label}>Метод 04 · Алмазное колесо</span>
      <h1 style={M4.h1}>Новая диагностика</h1>

      <div style={{ ...M4.field, marginBottom: 20 }}>
        <label style={M4.fieldLabel} htmlFor="company">Название компании</label>
        <input
          id="company" style={M4.input} value={companyName} maxLength={255}
          placeholder="Например: ООО Ромашка" onChange={e => setCompanyName(e.target.value)}
        />
      </div>

      <div style={{ marginBottom: 20 }}>
        <div style={M4.fieldLabel}>Вид диагностики</div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 8 }}>
          <button
            style={{ ...(mode === 'express' ? M4.choiceOn : M4.choice), opacity: expressBlocked ? 0.5 : 1 }}
            onClick={() => !expressBlocked && setMode('express')}
            disabled={expressBlocked}
          >
            <b>Экспресс</b><br />
            <span style={M4.choiceNote}>
              20 вопросов, по два на модуль · ≈ 7 минут · {expressBlocked ? 'уже использован' : 'бесплатно, один раз'}
            </span>
          </button>
          <button
            style={{ ...(mode === 'full' ? M4.choiceOn : M4.choice), opacity: fullBlocked ? 0.5 : 1 }}
            onClick={() => !fullBlocked && setMode('full')}
            disabled={fullBlocked}
          >
            <b>Полная</b><br />
            <span style={M4.choiceNote}>
              Все вопросы · ≈ 40 минут · {followup ? 'повтор, входит в стоимость'
                : fullBlocked ? 'входит в пакет «Метод 3 + Метод 4»' : 'из пакета'}
            </span>
          </button>
        </div>
        {fullBlocked && (
          <p style={M4.note}>
            Полная диагностика входит в пакет «Метод 3 + Метод 4».{' '}
            <a href="/dashboard" style={{ color: '#1a2540' }}>Оплатить пакет в кабинете</a>
          </p>
        )}
      </div>

      <div style={{ marginBottom: 8 }}>
        <div style={M4.fieldLabel}>
          Как устроена оплата у компании{mode === 'express' && ' (можно указать позже)'}
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 8 }}>
          {revenueOptions.map(o => (
            <button
              key={o.value}
              style={revenueModel === o.value ? M4.optOn : M4.opt}
              onClick={() => setRevenueModel(o.value as M4Profile['revenue_model'])}
            >
              {o.label}
            </button>
          ))}
        </div>
        <p style={M4.note}>От этого зависит часть вопросов о продукте.</p>
      </div>

      {mode === 'full' && followup && (
        <p style={M4.note}>
          Это повторная диагностика компании: она входит в стоимость первой и не расходует пакет.
          Отвечайте заново, по сегодняшнему положению дел — отчёт покажет, что изменилось.
        </p>
      )}
      {mode === 'full' && !followup && (
        <p style={M4.note}>
          Если по этой компании уже пройден экспресс, его ответы перенесутся в полную анкету.
        </p>
      )}

      {error && <p style={M4.warn}>{error}</p>}

      <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
        <button
          style={M4.btnGhost}
          onClick={() => (runs.length ? setPhase('list') : router.push('/dashboard'))}
        >
          ← Назад
        </button>
        <button style={M4.btnPrimary} onClick={start} disabled={busy}>
          {busy ? 'Создаём…' : 'Начать →'}
        </button>
      </div>
    </div></div>
  )
}

export default function M4Page() {
  return (
    <Suspense fallback={null}>
      <M4PageInner />
    </Suspense>
  )
}
