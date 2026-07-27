'use client'
import { usePathname } from 'next/navigation'

// Кнопка «Подробно» в разделах 04, 06, 07, 08 отчёта.
// Ведёт на страницу описания гексаграммы и запоминает, откуда пришли.
// В PDF не попадает: PDF собирается отдельной реализацией в pdf.py.
// Тег ссылки и его атрибуты держим в одной строке: многострочные теги
// теряются при вставке в редактор.

const STYLE = {
  display: 'inline-block',
  padding: '8px 16px',
  border: '1px solid #c0392b',
  borderRadius: 6,
  color: '#c0392b',
  fontFamily: 'sans-serif',
  fontSize: 12,
  letterSpacing: 1,
  textTransform: 'uppercase' as const,
  textDecoration: 'none',
}

export default function HexagramDetailsLink({ combo }: { combo?: string }) {
  const from = usePathname()
  const ok = typeof combo === 'string' && combo.length === 6
  if (ok === false) return null
  const href = '/hexagram/' + combo + '?from=' + encodeURIComponent(from || '')
  return (
    <div style={{ marginTop: 12 }}><a href={href} style={STYLE}>Подробно</a></div>
  )
}
