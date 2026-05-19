'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { getAssessment, getMe, reportDownloadUrl } from '@/lib/api'
import { AppNav } from '@/components/AppNav'

const HEX_TRIGRAMS = ['䷀','䷁','䷂','䷃','䷄','䷅','䷆','䷇','䷈','䷉','䷊','䷋','䷌','䷍','䷎','䷏','䷐','䷑','䷒','䷓','䷔','䷕','䷖','䷗','䷘','䷙','䷚','䷛','䷜','䷝','䷞','䷟','䷠','䷡','䷢','䷣','䷤','䷥','䷦','䷧','䷨','䷩','䷪','䷫','䷬','䷭','䷮','䷯','䷰','䷱','䷲','䷳','䷴','䷵','䷶','䷷','䷸','䷹','䷺','䷻','䷼','䷽','䷾','䷿']

function hexFor(combo: string): string {
  if (!combo || combo.length !== 6) return '䷀'
  const idx = parseInt([...combo].map(c => c === 'B' ? '1' : '0').join(''), 2)
  return HEX_TRIGRAMS[idx] || '䷀'
}

export default function ReportPage() {
  const router = useRouter()
  const params = useParams()
  const id = params.id as string

  const [assessment, setAssessment] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const init = async () => {
      try {
        await getMe()
        const data = await getAssessment(id)
        setAssessment(data)
      } catch {
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [id])

  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>Загрузка…</div>
  if (!assessment) return null

  const combo = assessment.method1_combination ?? 'AAAAAA'
  const hex = hexFor(combo)
  const report = assessment.reports?.[0]

  return (
    <>
      <AppNav current="dashboard" />
      <div className="report-shell">
        {/* TOC */}
        <nav className="report-toc">
          <h4>Содержание</h4>
          <a href="#cover" className="on">Обложка</a>
          <a href="#strategy">Стратегия</a>
          <a href="#lifecycle">Жизненный цикл</a>
          <a href="#marketing">Маркетинг</a>
          <a href="#management">Управление</a>
          <a href="#transition">Переход</a>
        </nav>

        <div className="report-body">
          {/* Обложка */}
          <div id="cover" className="report-cover">
            <div>
              <span className="label-red">Стратегический отчёт</span>
              <h1 className="h1-serif" style={{ marginTop: 10, marginBottom: 8 }}>
                Комбинация {combo}
              </h1>
              <p className="muted">
                Диагностика завершена · {new Date(assessment.created_at).toLocaleString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
              </p>
            </div>
            <div style={{ fontSize: 96, fontFamily: 'Georgia, serif', color: 'var(--blue)', lineHeight: 1 }}>
              {hex}
            </div>
          </div>

          {/* Статус отчёта */}
          <div style={{ marginBottom: 32 }}>
            {report ? (
              <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <span className="label-red" style={{ display: 'block', marginBottom: 6 }}>PDF-отчёт готов</span>
                  <p className="faint">Сгенерирован {report.generated_at ? new Date(report.generated_at).toLocaleString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}</p>
                </div>
                <a
                  href={reportDownloadUrl(report.id)}
                  className="btn btn-primary btn-lg"
                  target="_blank"
                  rel="noreferrer"
                >
                  ↓ Скачать PDF
                </a>
              </div>
            ) : (
              <div className="card" style={{ textAlign: 'center', padding: '32px' }}>
                <p className="muted">PDF-отчёт генерируется. Обычно это занимает меньше минуты.</p>
                <button className="btn btn-ghost" style={{ marginTop: 12 }} onClick={() => window.location.reload()}>
                  Обновить страницу
                </button>
              </div>
            )}
          </div>

          {/* Данные из БД или заглушка */}
          <div id="strategy" className="card" style={{ marginBottom: 20 }}>
            <span className="label-red" style={{ display: 'block', marginBottom: 10 }}>Стратегия</span>
            <h2 className="h2-serif" style={{ marginBottom: 12 }}>Гексаграмма {hex} · {combo}</h2>
            <p className="muted">
              Ваша стратегическая позиция определена. Подробные рекомендации — в PDF-отчёте.
            </p>
          </div>

          <div id="lifecycle" className="card" style={{ marginBottom: 20 }}>
            <span className="label-red" style={{ display: 'block', marginBottom: 10 }}>Жизненный цикл</span>
            <p className="muted">Анализ текущей стадии развития компании включён в PDF-отчёт.</p>
          </div>

          <div className="row" style={{ justifyContent: 'space-between', marginTop: 32 }}>
            <button className="btn btn-ghost" onClick={() => router.push('/dashboard')}>← К дашборду</button>
            {report && (
              <a href={reportDownloadUrl(report.id)} className="btn btn-primary" target="_blank" rel="noreferrer">
                ↓ Скачать PDF
              </a>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
