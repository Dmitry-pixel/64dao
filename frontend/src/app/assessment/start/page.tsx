'use client'
import { useRouter } from 'next/navigation'
import { AppNav } from '@/components/AppNav'

export default function AssessmentStartPage() {
  const router = useRouter()

  return (
    <>
      <AppNav />
      <div style={{ padding: '48px 60px', maxWidth: 980, margin: '0 auto' }}>
        <span className="label-red">Новая диагностика</span>
        <h1 className="h1-serif" style={{ marginTop: 10, marginBottom: 8 }}>Выберите метод</h1>
        <p className="muted" style={{ marginBottom: 40, maxWidth: 560 }}>
          Оба метода дают один результат — стратегическую гексаграмму и PDF-отчёт. Они различаются способом сбора данных.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, maxWidth: 860 }}>
          {/* Метод 1 */}
          <div
            className="card"
            style={{ cursor: 'pointer', transition: 'background 0.15s, border-color 0.15s' }}
            onClick={() => router.push('/assessment/method1')}
          >
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 16 }}>
              <span style={{ fontFamily: 'Georgia, serif', fontSize: 48, color: 'var(--blue)', lineHeight: 1 }}>䷀</span>
              <span className="label-red">Метод 1</span>
            </div>
            <h3 className="h3-serif" style={{ marginBottom: 10 }}>6 вопросов</h3>
            <p className="muted" style={{ marginBottom: 20, fontSize: 13 }}>
              Ответьте на 6 вопросов о текущем состоянии вашей компании. Каждый вопрос — выбор из двух вариантов. Занимает 5–10 минут.
            </p>
            <ul style={{ listStyle: 'none', fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', lineHeight: 1.8, marginBottom: 24 }}>
              <li>— Быстро и интуитивно</li>
              <li>— Не требует подготовки</li>
              <li>— Подходит для первой диагностики</li>
            </ul>
            <button className="btn btn-primary btn-block">Начать Метод 1 →</button>
          </div>

          {/* Метод 2 */}
          <div
            className="card"
            style={{ cursor: 'pointer', transition: 'background 0.15s, border-color 0.15s' }}
            onClick={() => router.push('/assessment/method2')}
          >
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 16 }}>
              <span style={{ fontFamily: 'Georgia, serif', fontSize: 48, color: 'var(--blue)', lineHeight: 1 }}>䷿</span>
              <span className="label-red">Метод 2</span>
            </div>
            <h3 className="h3-serif" style={{ marginBottom: 10 }}>Бизнес-модель</h3>
            <p className="muted" style={{ marginBottom: 20, fontSize: 13 }}>
              Оцените 9 блоков бизнес-модели Canvas по шкале от 1 до 5. Более точный результат. Занимает 15–20 минут.
            </p>
            <ul style={{ listStyle: 'none', fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', lineHeight: 1.8, marginBottom: 24 }}>
              <li>— Детальный анализ</li>
              <li>— Учитывает все аспекты бизнеса</li>
              <li>— Рекомендуется для повторной диагностики</li>
            </ul>
            <button className="btn btn-primary btn-block">Начать Метод 2 →</button>
          </div>
        </div>

        <div className="card-flat" style={{ marginTop: 32, maxWidth: 860 }}>
          <div style={{ display: 'flex', gap: 32, fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)' }}>
            <span>📄 PDF-отчёт со стратегией</span>
            <span>🎯 Анализ жизненного цикла</span>
            <span>💡 Рекомендации по управлению и маркетингу</span>
          </div>
        </div>
      </div>
    </>
  )
}
