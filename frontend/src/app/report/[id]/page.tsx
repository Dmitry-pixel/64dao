'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { getAssessment, getMe, getStrategyByCombo, generateReport, reportDownloadUrl } from '@/lib/api'
import type { Strategy, Assessment, AuthUser } from '@/lib/api'
import { AppNav } from '@/components/AppNav'

const API = process.env.NEXT_PUBLIC_API_URL || ''

const HEX_TRIGRAMS = ['䷀','䷁','䷂','䷃','䷄','䷅','䷆','䷇','䷈','䷉','䷊','䷋','䷌','䷍','䷎','䷏','䷐','䷑','䷒','䷓','䷔','䷕','䷖','䷗','䷘','䷙','䷚','䷛','䷜','䷝','䷞','䷟','䷠','䷡','䷢','䷣','䷤','䷥','䷦','䷧','䷨','䷩','䷪','䷫','䷬','䷭','䷮','䷯','䷰','䷱','䷲','䷳','䷴','䷵','䷶','䷷','䷸','䷹','䷺','䷻','䷼','䷽','䷾','䷿']

function hexFor(combo: string): string {
  if (!combo || combo.length !== 6) return '䷀'
  const idx = parseInt([...combo].map(c => c === 'B' ? '1' : '0').join(''), 2)
  return HEX_TRIGRAMS[idx] || '䷀'
}

const BMC_LABELS: Record<string, string> = {
  'Ключевые партнёры':      '01',
  'Ключевые активности':    '02',
  'Ключевые ресурсы':       '03',
  'Ценностное предложение': '04',
  'Отношения с клиентами':  '05',
  'Каналы':                 '06',
  'Сегменты клиентов':      '07',
  'Структура издержек':     '08',
  'Потоки доходов':         '09',
}

const BMC_ORDER = [
  'Ключевые партнёры',
  'Ключевые активности',
  'Ключевые ресурсы',
  'Ценностное предложение',
  'Отношения с клиентами',
  'Каналы',
  'Сегменты клиентов',
  'Структура издержек',
  'Потоки доходов',
]

function ScoreDots({ score }: { score: number }) {
  return (
    <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
      {[1,2,3,4,5].map(n => (
        <div key={n} style={{
          width: 10, height: 10, borderRadius: '50%',
          background: n <= score ? '#1e3a8a' : 'rgba(26,37,64,0.12)',
          transition: 'background 0.15s',
        }} />
      ))}
      <span style={{ fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.5)', marginLeft: 6 }}>
        {score} / 5
      </span>
    </div>
  )
}

function SectionBlock({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{
      background: 'rgba(255,255,255,0.72)',
      border: '1px solid rgba(26,37,64,0.09)',
      borderRadius: 10,
      padding: '22px 28px',
      marginBottom: 16,
    }}>
      <div style={{
        fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 2.5,
        textTransform: 'uppercase', color: '#c0392b', fontWeight: 600,
        marginBottom: 10,
      }}>{label}</div>
      {children}
    </div>
  )
}

function TextBody({ text }: { text: string }) {
  return (
    <p style={{
      fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.82)',
      lineHeight: 1.75, margin: 0, whiteSpace: 'pre-wrap',
    }}>{text}</p>
  )
}

// ── Method 1 Report ────────────────────────────────────────────────────────────

function Method1Report({
  assessment, strategy, user, onBack, onDownload, generatingPdf,
}: {
  assessment: Assessment
  strategy: Strategy | null
  user: AuthUser
  onBack: () => void
  onDownload: () => void
  generatingPdf: boolean
}) {
  const combo = assessment.method1_combination ?? 'AAAAAA'
  const hex = hexFor(combo)
  const companyName = assessment.company_name || user.company_name || user.full_name || 'Компания'
  const dateStr = new Date(assessment.created_at).toLocaleDateString('ru-RU', {
    day: 'numeric', month: 'long', year: 'numeric'
  })

  return (
    <div style={{ maxWidth: 820, margin: '0 auto', padding: '48px 40px 80px' }}>

      {/* Back + PDF */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 40 }}>
        <button onClick={onBack} className="btn btn-ghost" style={{ fontSize: 13, padding: '8px 16px' }}>
          ← Назад
        </button>
        <button
          className="btn btn-primary"
          onClick={onDownload}
          disabled={generatingPdf}
          style={{ opacity: generatingPdf ? 0.6 : 1 }}
        >
          {generatingPdf ? 'Формируем PDF…' : '↓ Скачать PDF'}
        </button>
      </div>

      {/* Cover */}
      <div style={{
        background: '#1a2540',
        borderRadius: 14,
        padding: '48px 52px',
        marginBottom: 32,
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Decorative hex bg */}
        <div style={{
          position: 'absolute', right: 40, top: '50%', transform: 'translateY(-50%)',
          fontFamily: 'Georgia,serif', fontSize: 200, color: 'rgba(255,255,255,0.04)',
          lineHeight: 1, userSelect: 'none', pointerEvents: 'none',
        }}>{hex}</div>

        <div style={{
          fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 3,
          textTransform: 'uppercase', color: '#c0392b', fontWeight: 700, marginBottom: 20,
        }}>СТРАТЕГИЧЕСКИЙ ОТЧЁТ 64 ДАО</div>

        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 28, marginBottom: 28 }}>
          <div style={{ fontFamily: 'Georgia,serif', fontSize: 110, color: 'rgba(255,255,255,0.9)', lineHeight: 1, flexShrink: 0 }}>
            {hex}
          </div>
          <div style={{ paddingTop: 8 }}>
            {strategy?.title && (
              <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 34, fontWeight: 400, color: '#fff', margin: '0 0 10px', lineHeight: 1.2 }}>
                {strategy.title}
              </h1>
            )}
            {strategy?.stratagema_title && (
              <div style={{ fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(255,255,255,0.55)', marginBottom: 6 }}>
                {strategy.stratagema_title}
              </div>
            )}
          </div>
        </div>

        <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 18, display: 'flex', gap: 36 }}>
          <div>
            <div style={{ fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 1.5, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 4 }}>Компания</div>
            <div style={{ fontFamily: 'Georgia,serif', fontSize: 16, color: 'rgba(255,255,255,0.85)' }}>{companyName}</div>
          </div>
          <div>
            <div style={{ fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 1.5, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 4 }}>Дата</div>
            <div style={{ fontFamily: 'Georgia,serif', fontSize: 16, color: 'rgba(255,255,255,0.85)' }}>{dateStr}</div>
          </div>
        </div>
      </div>

      {/* Strategy image */}
      {strategy?.image_url && (
        <div style={{ marginBottom: 24, borderRadius: 10, overflow: 'hidden', border: '1px solid rgba(26,37,64,0.08)' }}>
          <img src={`${API}${strategy.image_url}`} alt={strategy.title ?? ''} style={{ width: '100%', display: 'block' }} />
        </div>
      )}

      {/* Lifecycle */}
      {(strategy?.lifecycle_stage || strategy?.lifecycle_description) && (
        <SectionBlock label="Жизненный цикл">
          {strategy.lifecycle_stage && (
            <h3 style={{ fontFamily: 'Georgia,serif', fontSize: 20, fontWeight: 400, color: '#1a2540', margin: '0 0 10px' }}>
              {strategy.lifecycle_stage}
            </h3>
          )}
          {strategy.lifecycle_description && <TextBody text={strategy.lifecycle_description} />}
        </SectionBlock>
      )}

      {/* Scenario */}
      {strategy?.scenario_text && (
        <SectionBlock label="Сценарий">
          <TextBody text={strategy.scenario_text} />
        </SectionBlock>
      )}

      {/* Marketing */}
      {strategy?.marketing_text && (
        <SectionBlock label="Маркетинг">
          <TextBody text={strategy.marketing_text} />
        </SectionBlock>
      )}

      {/* Management */}
      {strategy?.management_text && (
        <SectionBlock label="Управление">
          <TextBody text={strategy.management_text} />
        </SectionBlock>
      )}

      {/* Transition */}
      {(strategy?.transition_title || strategy?.transition_description) && (
        <SectionBlock label="Переход">
          {strategy.transition_title && (
            <h3 style={{ fontFamily: 'Georgia,serif', fontSize: 20, fontWeight: 400, color: '#1a2540', margin: '0 0 10px' }}>
              {strategy.transition_lifecycle_stage
                ? `${strategy.transition_title} · ${strategy.transition_lifecycle_stage}`
                : strategy.transition_title}
            </h3>
          )}
          {strategy.transition_description && <TextBody text={strategy.transition_description} />}
        </SectionBlock>
      )}

      {/* No strategy */}
      {!strategy && (
        <SectionBlock label="Стратегия">
          <p style={{ fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.5)', margin: 0 }}>
            Стратегия для комбинации {combo} ещё не опубликована. Полные рекомендации — в PDF-отчёте.
          </p>
        </SectionBlock>
      )}

    </div>
  )
}

// ── Method 2 Report ────────────────────────────────────────────────────────────

function Method2Report({
  assessment, user, onBack, onDownload, generatingPdf,
}: {
  assessment: Assessment
  user: AuthUser
  onBack: () => void
  onDownload: () => void
  generatingPdf: boolean
}) {
  const method2 = assessment.method2_data as Record<string, { score: number; text: string }> | null
  const companyName = assessment.company_name || user.company_name || user.full_name || 'Компания'
  const dateStr = new Date(assessment.created_at).toLocaleDateString('ru-RU', {
    day: 'numeric', month: 'long', year: 'numeric'
  })

  const blocks = BMC_ORDER
    .filter(key => method2?.[key])
    .map(key => ({ title: key, num: BMC_LABELS[key] ?? '', ...method2![key] }))

  return (
    <div style={{ maxWidth: 820, margin: '0 auto', padding: '48px 40px 80px' }}>

      {/* Back + PDF */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 40 }}>
        <button onClick={onBack} className="btn btn-ghost" style={{ fontSize: 13, padding: '8px 16px' }}>
          ← Назад
        </button>
        <button
          className="btn btn-primary"
          onClick={onDownload}
          disabled={generatingPdf}
          style={{ opacity: generatingPdf ? 0.6 : 1 }}
        >
          {generatingPdf ? 'Формируем PDF…' : '↓ Скачать PDF'}
        </button>
      </div>

      {/* Cover */}
      <div style={{
        background: '#1a2540',
        borderRadius: 14,
        padding: '48px 52px',
        marginBottom: 32,
      }}>
        <div style={{
          fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 3,
          textTransform: 'uppercase', color: '#c0392b', fontWeight: 700, marginBottom: 20,
        }}>БИЗНЕС МОДЕЛЬ ОТЧЁТ 64 ДАО</div>

        <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 34, fontWeight: 400, color: '#fff', margin: '0 0 24px', lineHeight: 1.2 }}>
          Анализ бизнес-модели
        </h1>

        <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 18, display: 'flex', gap: 36 }}>
          <div>
            <div style={{ fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 1.5, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 4 }}>Компания</div>
            <div style={{ fontFamily: 'Georgia,serif', fontSize: 16, color: 'rgba(255,255,255,0.85)' }}>{companyName}</div>
          </div>
          <div>
            <div style={{ fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 1.5, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', marginBottom: 4 }}>Дата</div>
            <div style={{ fontFamily: 'Georgia,serif', fontSize: 16, color: 'rgba(255,255,255,0.85)' }}>{dateStr}</div>
          </div>
        </div>
      </div>

      {blocks.length > 0 ? (
        <>
          {/* Сводка оценок — сетка 3×3 */}
          <div style={{ marginBottom: 10 }}>
            <div style={{
              fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 2.5,
              textTransform: 'uppercase', color: '#c0392b', fontWeight: 600, marginBottom: 12,
            }}>Оценка блоков</div>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 10,
              marginBottom: 32,
            }}>
              {blocks.map(block => (
                <div key={block.title} style={{
                  background: 'rgba(255,255,255,0.72)',
                  border: '1px solid rgba(26,37,64,0.09)',
                  borderRadius: 10,
                  padding: '16px 18px',
                }}>
                  <div style={{
                    fontFamily: 'sans-serif', fontSize: 11, fontWeight: 600,
                    color: '#1a2540', marginBottom: 10,
                  }}>{block.num} · {block.title}</div>
                  <ScoreDots score={block.score} />
                </div>
              ))}
            </div>
          </div>

          {/* Комментарии */}
          <div style={{
            fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 2.5,
            textTransform: 'uppercase', color: '#c0392b', fontWeight: 600, marginBottom: 12,
          }}>Комментарии</div>
          {blocks.map(block => (
            <SectionBlock key={block.title} label={`${block.num} · ${block.title}`}>
              <div style={{ marginBottom: block.text ? 14 : 0 }}>
                <ScoreDots score={block.score} />
              </div>
              {block.text
                ? <TextBody text={block.text} />
                : <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.35)', margin: 0, fontStyle: 'italic' }}>Комментарий не добавлен</p>
              }
            </SectionBlock>
          ))}
        </>
      ) : (
        <SectionBlock label="Бизнес-модель">
          <p style={{ fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.5)', margin: 0 }}>
            Данные бизнес-модели не заполнены.
          </p>
        </SectionBlock>
      )}

    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function ReportPage() {
  const router = useRouter()
  const params = useParams()
  const id = params.id as string

  const [assessment, setAssessment] = useState<Assessment | null>(null)
  const [strategy, setStrategy] = useState<Strategy | null>(null)
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [isAdmin, setIsAdmin] = useState(false)
  const [generatingPdf, setGeneratingPdf] = useState(false)

  useEffect(() => {
    const init = async () => {
      try {
        const [me, data] = await Promise.all([getMe(), getAssessment(id)])
        setUser(me)
        setAssessment(data)
        setIsAdmin(me.role === 'admin')

        // If method1, try to load strategy
        if (data.method1_combination && !data.method2_data) {
          try {
            const s = await getStrategyByCombo(data.method1_combination)
            setStrategy(s)
          } catch {
            // unpublished — that's OK, report still shows
          }
        }
      } catch {
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [id])

  const handleDownload = async () => {
    setGeneratingPdf(true)
    try {
      const report = await generateReport(id)
      window.open(reportDownloadUrl(report.id), '_blank')
    } catch {
      alert('Не удалось сформировать PDF. Попробуйте ещё раз.')
    } finally {
      setGeneratingPdf(false)
    }
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>
      Загрузка…
    </div>
  )
  if (!assessment || !user) return null

  const isMethod2 = !!assessment.method2_data && Object.keys(assessment.method2_data).length > 0
  const backUrl = isAdmin ? '/admin/my-reports' : '/dashboard'

  return (
    <>
      <AppNav current="dashboard" />
      {isMethod2 ? (
        <Method2Report
          assessment={assessment}
          user={user}
          onBack={() => router.push(backUrl)}
          onDownload={handleDownload}
          generatingPdf={generatingPdf}
        />
      ) : (
        <Method1Report
          assessment={assessment}
          strategy={strategy}
          user={user}
          onBack={() => router.push(backUrl)}
          onDownload={handleDownload}
          generatingPdf={generatingPdf}
        />
      )}
    </>
  )
}
