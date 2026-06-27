'use client'

import { useEffect, useState } from 'react'

const COOKIE_KEY = 'cookie-consent'

/** Баннер согласия с cookie. Исчезает после клика, запоминает выбор в localStorage. */
export default function CookieBanner() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    try {
      if (localStorage.getItem(COOKIE_KEY) !== '1') {
        setVisible(true)
      }
    } catch {
      // приватный режим — показываем без сохранения
      setVisible(true)
    }
  }, [])

  function accept() {
    try {
      localStorage.setItem(COOKIE_KEY, '1')
    } catch {}
    setVisible(false)
  }

  if (!visible) return null

  return (
    <div
      style={{
        position: 'fixed',
        left: 16,
        right: 16,
        bottom: 16,
        zIndex: 50,
        maxWidth: 768,
        margin: '0 auto',
        borderRadius: 2,
        border: '1px solid var(--border)',
        background: 'var(--card)',
        padding: 20,
        boxShadow: '0 20px 60px -20px rgba(0,0,0,0.3)',
      }}
    >
      <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: 'var(--foreground)' }}>
        Мы используем файлы cookie и рекомендательные технологии. Подробно описали в{' '}
        <a href="/documents/privacy-policy" style={{ color: 'var(--accent)', textDecoration: 'underline' }}>
          Политике конфиденциальности
        </a>{' '}
        (ничего лишнего не собираем и за границу не передаём). Вы можете отключить cookies в настройках браузера.
      </p>
      <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <button
          type="button"
          onClick={accept}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 2,
            background: 'var(--accent)',
            padding: '10px 20px',
            fontSize: 14,
            fontWeight: 500,
            color: 'var(--accent-foreground)',
            border: 'none',
            cursor: 'pointer',
          }}
        >
          Соглашаюсь с использованием cookies
        </button>
      </div>
    </div>
  )
}
