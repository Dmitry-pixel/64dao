'use client'
import { useRouter } from 'next/navigation'

// Кнопка «Назад»: возвращает на предыдущую страницу истории, а при прямом
// заходе по ссылке уводит на fallback.
// Тег и атрибуты держим в одной строке: многострочные теги теряются при вставке.

const STYLE = {
  display: 'inline-block',
  padding: '6px 14px',
  border: '1px solid rgba(26,37,64,0.25)',
  borderRadius: 6,
  background: 'transparent',
  color: '#1e3a8a',
  fontFamily: 'sans-serif',
  fontSize: 12,
  letterSpacing: 1,
  textTransform: 'uppercase' as const,
  cursor: 'pointer',
}

export default function BackButton({ fallback = '/dashboard', label = 'Назад' }: { fallback?: string; label?: string }) {
  const router = useRouter()
  const go = () => {
    if (typeof window === 'undefined') return
    if (window.history.length > 1) router.back()
    else router.push(fallback)
  }
  return (
    <div style={{ marginBottom: 16 }}><button onClick={go} style={STYLE}>← {label}</button></div>
  )
}
