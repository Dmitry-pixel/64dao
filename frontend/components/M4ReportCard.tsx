'use client'
/**
 * Строка Метода 4 в списке «Мои отчёты».
 *
 * Отдельный компонент по той же причине, что M3ReportCard: у прогона своя
 * единица (экспресс или полная, модули вместо гексаграммы), свой адрес отчёта
 * и свой эндпоинт PDF. Используется в кабинете и в админской «Мои отчёты».
 */
import { useRouter } from 'next/navigation'
import type { M4RunOut } from '@/lib/m4'

const STATUS_LABEL: Record<string, string> = {
  draft: 'Черновик',
  filled: 'Анкета заполнена',
  calculated: 'Готов',
}

export function m4RowDate(r: M4RunOut): string {
  return r.calculated_at || r.created_at
}

export default function M4ReportCard(
  { r, n, onDelete, deleting = false }: {
    r: M4RunOut
    n: number
    onDelete?: (run: M4RunOut) => void
    deleting?: boolean
  },
) {
  const router = useRouter()
  const done = r.status === 'calculated'
  const name = r.company_name || '—'
  const btn = {
    fontFamily: 'sans-serif', fontSize: 12, color: '#1a2540', background: 'none',
    border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6, padding: '6px 12px',
    cursor: 'pointer', textDecoration: 'none',
  } as const

  return (
    <div
      className="dash-card-mobile"
      style={{
        display: 'flex', gap: 18, alignItems: 'flex-start',
        background: 'rgba(255,255,255,0.7)', border: '1px solid rgba(26,37,64,0.1)',
        borderRadius: 8, padding: '18px 22px', cursor: done ? 'pointer' : 'default',
      }}
      onClick={() => done && router.push(`/m4/${r.id}/result`)}
    >
      <div style={{ fontFamily: 'Georgia,serif', fontSize: 22, color: 'rgba(26,37,64,0.25)', minWidth: 32 }}>
        {String(n).padStart(2, '0')}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.4)', marginBottom: 4 }}>
          {new Date(m4RowDate(r)).toLocaleString('ru-RU', {
            day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit',
          })}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{
            fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 1.5, textTransform: 'uppercase',
            fontWeight: 700, color: '#c0392b', background: 'rgba(192,57,43,0.08)',
            border: '1px solid rgba(192,57,43,0.2)', borderRadius: 4, padding: '2px 8px',
          }}>Метод 04</span>
          <span style={{ fontFamily: 'Georgia,serif', fontSize: 17, color: '#1a2540' }}>
            Алмазное колесо · {name}
          </span>
        </div>
        <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.5)', marginTop: 4 }}>
          {r.mode === 'express' ? 'Экспресс-диагностика' : 'Полная диагностика'}
          {!done && ` · отвечено ${r.progress.answered} из ${r.progress.required}`}
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-end' }}>
        <span style={{
          fontFamily: 'sans-serif', fontSize: 11, padding: '3px 10px', borderRadius: 4,
          color: done ? '#166534' : 'rgba(26,37,64,0.6)',
          background: done ? 'rgba(22,101,52,0.08)' : 'rgba(26,37,64,0.06)',
        }}>{STATUS_LABEL[r.status] ?? r.status}</span>
        {done ? (
          <a href={`/api/m4/runs/${r.id}/pdf`} target="_blank" rel="noreferrer"
            onClick={e => e.stopPropagation()} style={btn}>Скачать PDF</a>
        ) : (
          <button onClick={e => { e.stopPropagation(); router.push(`/m4/${r.id}`) }} style={btn}>
            Продолжить →
          </button>
        )}
        {onDelete && (
          <button
            onClick={e => { e.stopPropagation(); onDelete(r) }}
            disabled={deleting}
            style={{ ...btn, color: '#c0392b', border: '1px solid rgba(192,57,43,0.25)', opacity: deleting ? 0.6 : 1 }}
          >{deleting ? 'Удаляем…' : 'Удалить'}</button>
        )}
      </div>
    </div>
  )
}
