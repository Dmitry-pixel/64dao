'use client'
/**
 * Строка Метода 3 в списке «Мои отчёты».
 *
 * Отдельный компонент, а не третья ветка внутри карточки ассессмента:
 * у портфеля другая единица (направления, а не гексаграмма), другой адрес
 * отчёта и другой эндпоинт PDF. Общий компонент с двумя наборами полей
 * читался бы хуже двух простых.
 *
 * Используется и в кабинете, и в админской странице «Мои отчёты» — иначе
 * появились бы две копии одной разметки, расходящиеся при первой правке.
 */
import { useRouter } from 'next/navigation'
import type { M3Portfolio } from '@/lib/m3'

const STATUS_LABEL: Record<string, string> = {
  draft: 'Черновик',
  filled: 'Анкета заполнена',
  calculated: 'Готов',
}

export function m3RowDate(p: M3Portfolio): string {
  // Сортировка общего списка идёт по дате: у рассчитанного портфеля
  // осмысленна дата расчёта, у незавершённого — дата создания.
  // updated_at сервер не отдаёт намеренно (см. M3PortfolioOut).
  return p.calculated_at || p.created_at
}

export default function M3ReportCard(
  { p, n, onDelete, deleting = false }: {
    p: M3Portfolio
    n: number
    /** Не передан — кнопки удаления нет: страница сама решает, показывать ли её. */
    onDelete?: (portfolio: M3Portfolio) => void
    deleting?: boolean
  },
) {
  const router = useRouter()
  const done = p.status === 'calculated'
  const name = p.company_name || p.title || '—'

  return (
    <div
      className="dash-card-mobile"
      style={{
        display: 'flex', gap: 18, alignItems: 'flex-start',
        background: 'rgba(255,255,255,0.7)', border: '1px solid rgba(26,37,64,0.1)',
        borderRadius: 8, padding: '18px 22px', cursor: done ? 'pointer' : 'default',
      }}
      onClick={() => done && router.push(`/report/m3/${p.id}`)}
    >
      <div style={{ fontFamily: 'Georgia,serif', fontSize: 22, color: 'rgba(26,37,64,0.25)', minWidth: 32 }}>
        {String(n).padStart(2, '0')}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.4)', marginBottom: 4 }}>
          {new Date(m3RowDate(p)).toLocaleString('ru-RU', {
            day: 'numeric', month: 'long', year: 'numeric',
            hour: '2-digit', minute: '2-digit',
          })}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{
            fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 1.5,
            textTransform: 'uppercase', fontWeight: 700, color: '#c0392b',
            background: 'rgba(192,57,43,0.08)', border: '1px solid rgba(192,57,43,0.2)',
            borderRadius: 4, padding: '2px 8px',
          }}>Метод 03</span>
          <span style={{ fontFamily: 'Georgia,serif', fontSize: 17, color: '#1a2540' }}>
            Матрица силы · {name}
          </span>
        </div>
        <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.5)', marginTop: 4 }}>
          Направлений: {p.objects?.length ?? 0}
          {p.title && p.title !== name ? ` · ${p.title}` : ''}
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-end' }}>
        <span style={{
          fontFamily: 'sans-serif', fontSize: 11, padding: '3px 10px', borderRadius: 4,
          color: done ? '#166534' : 'rgba(26,37,64,0.6)',
          background: done ? 'rgba(22,101,52,0.08)' : 'rgba(26,37,64,0.06)',
        }}>{STATUS_LABEL[p.status] ?? p.status}</span>
        {done ? (
          <a
            href={`/api/reports/m3/${p.id}/download`}
            target="_blank"
            rel="noreferrer"
            onClick={e => e.stopPropagation()}
            style={{
              fontFamily: 'sans-serif', fontSize: 12, color: '#1a2540',
              border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6,
              padding: '6px 12px', textDecoration: 'none',
            }}
          >Скачать PDF</a>
        ) : (
          <button
            onClick={e => { e.stopPropagation(); router.push(`/m3/${p.id}/questionnaire`) }}
            style={{
              fontFamily: 'sans-serif', fontSize: 12, color: '#1a2540',
              background: 'none', border: '1px solid rgba(26,37,64,0.2)',
              borderRadius: 6, padding: '6px 12px', cursor: 'pointer',
            }}
          >Продолжить →</button>
        )}
        {onDelete && (
          <button
            onClick={e => { e.stopPropagation(); onDelete(p) }}
            disabled={deleting}
            style={{
              fontFamily: 'sans-serif', fontSize: 12, color: '#c0392b',
              background: 'none', border: '1px solid rgba(192,57,43,0.25)',
              borderRadius: 6, padding: '6px 12px', cursor: 'pointer',
              opacity: deleting ? 0.6 : 1,
            }}
          >{deleting ? 'Удаляем…' : 'Удалить'}</button>
        )}
      </div>
    </div>
  )
}
