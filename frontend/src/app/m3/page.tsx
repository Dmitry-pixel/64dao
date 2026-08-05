'use client'

// force-dynamic + Suspense: useSearchParams иначе не даёт странице
// пререндериться статически (Next 14 App Router).
export const dynamic = 'force-dynamic'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import PortfolioForm from '@/components/m3/PortfolioForm'
import {
  createPortfolio, listIndustries, listPortfolios, putObjects,
  type M3Industry, type M3ObjectIn, type M3Portfolio,
} from '@/lib/m3'

const P = {
  page: { minHeight: '100vh', background: '#e8e4db' } as React.CSSProperties,
  stage: { maxWidth: 860, margin: '0 auto', padding: '64px 40px' } as React.CSSProperties,
  label: {
    fontFamily: 'sans-serif', fontSize: 11, letterSpacing: 2,
    textTransform: 'uppercase' as const, color: '#c0392b', fontWeight: 600,
  } as React.CSSProperties,
  h1: {
    fontFamily: 'Georgia,serif', fontSize: 34, fontWeight: 400,
    color: '#1a2540', margin: '10px 0 12px',
  } as React.CSSProperties,
  text: {
    fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.65)',
    lineHeight: 1.7, marginBottom: 18, maxWidth: 620,
  } as React.CSSProperties,
  field: { display: 'flex', flexDirection: 'column' as const, gap: 5, maxWidth: 420 } as React.CSSProperties,
  fieldLabel: {
    fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.6)',
  } as React.CSSProperties,
  input: {
    padding: '9px 11px', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6,
    fontFamily: 'sans-serif', fontSize: 14, color: '#1a2540', background: '#fff',
    width: '100%', boxSizing: 'border-box' as const,
  } as React.CSSProperties,
  btnPrimary: {
    display: 'inline-flex', alignItems: 'center', gap: 8, padding: '11px 22px',
    background: '#1a2540', color: '#fff', border: 'none', borderRadius: 6,
    fontFamily: 'sans-serif', fontSize: 14, cursor: 'pointer',
  } as React.CSSProperties,
  btnGhost: {
    padding: '11px 18px', background: 'none', border: '1px solid rgba(26,37,64,0.2)',
    borderRadius: 6, fontFamily: 'sans-serif', fontSize: 14, cursor: 'pointer',
    color: '#1a2540',
  } as React.CSSProperties,
  warn: {
    fontFamily: 'sans-serif', fontSize: 13, color: '#c0392b', lineHeight: 1.6,
  } as React.CSSProperties,
  note: {
    fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.5)',
    lineHeight: 1.6, marginTop: 10,
  } as React.CSSProperties,
  listRow: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    gap: 12, padding: '11px 0', borderBottom: '1px solid rgba(26,37,64,0.08)',
    fontFamily: 'sans-serif', fontSize: 14, color: '#1a2540',
  } as React.CSSProperties,
  status: {
    fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.5)',
  } as React.CSSProperties,
}

const STATUS_LABEL: Record<string, string> = {
  draft: 'черновик',
  filled: 'анкета заполняется',
  calculated: 'рассчитан',
}

type Phase = 'loading' | 'list' | 'setup' | 'objects'

function M3PageInner() {
  const router = useRouter()
  // Название компании приходит из /assessment: оно вводится ПЕРЕД
  // диагностикой, как в Методах 1 и 2. Второй формы ввода здесь нет —
  // поле ниже предзаполнено и остаётся редактируемым.
  const companyParam = useSearchParams().get('company') || ''

  const [phase, setPhase] = useState<Phase>('loading')
  const [industries, setIndustries] = useState<M3Industry[]>([])
  const [portfolios, setPortfolios] = useState<M3Portfolio[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)

  const [title, setTitle] = useState('')
  const [companyName, setCompanyName] = useState(companyParam)
  const [industryId, setIndustryId] = useState<number | null>(null)
  const [portfolio, setPortfolio] = useState<M3Portfolio | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([listIndustries(), listPortfolios()])
      .then(([inds, ports]) => {
        setIndustries(inds)
        setPortfolios(ports)
        // Пришли из «Новой диагностики» — сразу форма нового портфеля:
        // пользователь уже выбрал метод и ввёл название компании, список
        // прошлых портфелей на этом шаге его не спрашивали.
        setPhase(companyParam || !ports.length ? 'setup' : 'list')
      })
      .catch((e: any) => setLoadError(
        e?.status === 404
          ? 'Раздел пока недоступен.'
          : e?.message || 'Не удалось загрузить данные.',
      ))
  }, [])

  async function startPortfolio() {
    setBusy(true)
    setError(null)
    try {
      const p = await createPortfolio({
        title: title.trim() || null,
        company_name: companyName.trim() || null,
        industry_id: industryId,
      })
      setPortfolio(p)
      setPhase('objects')
    } catch (e: any) {
      setError(e?.message || 'Не удалось создать портфель.')
    } finally {
      setBusy(false)
    }
  }

  async function saveObjects(objects: M3ObjectIn[]) {
    if (!portfolio) return
    setBusy(true)
    setError(null)
    try {
      await putObjects(portfolio.id, objects)
      router.push(`/m3/${portfolio.id}/questionnaire`)
    } catch (e: any) {
      setError(e?.message || 'Не удалось сохранить направления.')
      setBusy(false)
    }
  }

  if (loadError) return (
    <div style={P.page}><div style={P.stage}>
      <p style={P.warn}>{loadError}</p>
      <button style={P.btnGhost} onClick={() => router.push('/dashboard')}>← В кабинет</button>
    </div></div>
  )

  if (phase === 'loading') return (
    <div style={P.page}><div style={P.stage}>
      <p style={{ fontFamily: 'sans-serif', color: 'rgba(26,37,64,0.6)' }}>Загрузка…</p>
    </div></div>
  )

  if (phase === 'list') return (
    <div style={P.page}><div style={P.stage}>
      <span style={P.label}>Метод 03 · матрица силы</span>
      <h1 style={P.h1}>Ваши портфели</h1>
      <p style={P.text}>
        Метод отвечает на вопрос, между какими направлениями и в каком порядке
        распределять ресурс. Этим он отличается от Методов 1 и 2: те говорят,
        в каком состоянии компания, этот — куда направить деньги.
      </p>

      {portfolios.map(p => (
        <div key={p.id} style={P.listRow}>
          <span>{p.company_name || p.title || 'Без названия'} · {p.objects.length} направлений</span>
          <span style={P.status}>{STATUS_LABEL[p.status] ?? p.status}</span>
          <button
            style={P.btnGhost}
            onClick={() => router.push(
              p.status === 'calculated'
                ? `/report/m3/${p.id}`
                : `/m3/${p.id}/questionnaire`,
            )}
          >
            {p.status === 'calculated' ? 'Отчёт' : 'Продолжить'} →
          </button>
        </div>
      ))}

      <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
        <button style={P.btnGhost} onClick={() => router.push('/dashboard')}>← В кабинет</button>
        <button style={P.btnPrimary} onClick={() => setPhase('setup')}>Новый портфель →</button>
      </div>
    </div></div>
  )

  if (phase === 'setup') return (
    <div style={P.page}><div style={P.stage}>
      <span style={P.label}>Метод 03 · матрица силы</span>
      <h1 style={P.h1}>Новый портфель</h1>
      <p style={P.text}>
        Область задаёт веса линий и наследуется направлениями — у каждого её
        можно переопределить. Веса клиент не настраивает и не видит: они
        экспертные, и пересматриваются по мере накопления отчётов.
      </p>

      <div style={{ ...P.field, marginBottom: 16 }}>
        <label style={P.fieldLabel} htmlFor="company">Название компании</label>
        <input
          id="company"
          style={P.input}
          value={companyName}
          maxLength={255}
          placeholder="Например: ООО Ромашка"
          onChange={e => setCompanyName(e.target.value)}
        />
        <span style={{ ...P.fieldLabel, fontSize: 11, opacity: 0.75 }}>
          Идёт в заголовок отчёта.
        </span>
      </div>

      <div style={{ ...P.field, marginBottom: 16 }}>
        <label style={P.fieldLabel} htmlFor="title">Название портфеля</label>
        <input
          id="title"
          style={P.input}
          value={title}
          maxLength={255}
          placeholder="Например, производство косметики"
          onChange={e => setTitle(e.target.value)}
        />
      </div>

      <div style={P.field}>
        <label style={P.fieldLabel} htmlFor="industry">Основная область</label>
        <select
          id="industry"
          style={P.input}
          value={industryId ?? ''}
          onChange={e => setIndustryId(e.target.value === '' ? null : Number(e.target.value))}
        >
          <option value="">Не выбрана — универсальные веса</option>
          {industries.map(i => (
            <option key={i.id} value={i.id}>{i.name}</option>
          ))}
        </select>
      </div>

      <p style={P.note}>
        Если направления охватывают разные отрасли, укажите здесь основную,
        а у остальных переопределите на следующем шаге. Единый пресет на весь
        портфель исказил бы оценку.
      </p>

      {error && <p style={P.warn}>{error}</p>}

      <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
        <button
          style={P.btnGhost}
          onClick={() => (portfolios.length ? setPhase('list') : router.push('/dashboard'))}
        >
          ← Назад
        </button>
        <button style={P.btnPrimary} onClick={startPortfolio} disabled={busy}>
          {busy ? 'Создаём…' : 'Дальше →'}
        </button>
      </div>
    </div></div>
  )

  return (
    <div style={P.page}><div style={P.stage}>
      <PortfolioForm
        industries={industries}
        portfolioIndustryId={industryId}
        submitting={busy}
        error={error}
        onSubmit={saveObjects}
        onCancel={() => setPhase('setup')}
      />
    </div></div>
  )
}


export default function M3Page() {
  return (
    <Suspense fallback={null}>
      <M3PageInner />
    </Suspense>
  )
}
