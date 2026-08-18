import type { Metadata } from 'next'
import type { CSSProperties } from 'react'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Не открывается страница оплаты — 64 ДАО',
  description:
    'Что делать, если браузер блокирует страницу оплаты Точки: сертификаты Минцифры или браузер со встроенной поддержкой.',
}

const CARD: CSSProperties = {
  background: 'rgba(255,255,255,0.7)',
  border: '1px solid rgba(26,37,64,0.1)',
  borderRadius: 10,
  padding: '18px 20px',
  marginBottom: 16,
}

const H2: CSSProperties = {
  fontFamily: 'Georgia,serif',
  fontSize: 20,
  color: '#1a2540',
  margin: '0 0 10px',
}

const P: CSSProperties = {
  fontFamily: 'sans-serif',
  fontSize: 14,
  lineHeight: 1.6,
  color: 'rgba(26,37,64,0.8)',
  margin: '0 0 10px',
}

export default function PaymentCertificateHelpPage() {
  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: '40px 20px' }}>
      <Link
        href="/dashboard"
        style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.55)', textDecoration: 'none' }}
      >
        &larr; в личный кабинет
      </Link>

      <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, color: '#1a2540', margin: '16px 0 8px' }}>
        Не открывается страница оплаты
      </h1>

      <p style={{ ...P, marginBottom: 24 }}>
        Если после нажатия «Купить» браузер показывает предупреждение о защищённом
        соединении и не пускает дальше — проблема не в вашем компьютере и не в нашем
        сайте.
      </p>

      <div style={CARD}>
        <h2 style={H2}>Почему так происходит</h2>
        <p style={P}>
          Оплату принимает Точка Банк, страница оплаты находится на его домене.
          Российские банки переходят на TLS-сертификаты удостоверяющего центра
          Минцифры России. Chrome, Safari и Edge такие сертификаты по умолчанию
          не признают и блокируют страницу.
        </p>
        <p style={{ ...P, margin: 0 }}>
          Сам платёж при этом безопасен: сертификат государственный, блокировка —
          следствие того, что этого центра нет в списке доверенных у браузера.
        </p>
      </div>

      <div style={CARD}>
        <h2 style={H2}>Способ 1. Открыть в другом браузере</h2>
        <p style={{ ...P, margin: 0 }}>
          Самый быстрый путь. В Яндекс.Браузере и браузере Atom сертификаты
          Минцифры уже встроены — скопируйте адрес страницы оплаты и откройте
          её там, устанавливать ничего не нужно.
        </p>
      </div>

      <div style={CARD}>
        <h2 style={H2}>Способ 2. Установить сертификаты</h2>
        <p style={P}>
          Подойдёт, если вы регулярно пользуетесь сайтами российских банков
          и госсервисов. Инструкции для Windows, macOS, Android, iOS и Linux
          опубликованы на Госуслугах:
        </p>
        <p style={{ ...P, margin: 0 }}>
          <a
            href="https://www.gosuslugi.ru/crt"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: '#c0392b' }}
          >
            gosuslugi.ru/crt &rarr;
          </a>
        </p>
      </div>

      <div style={CARD}>
        <h2 style={H2}>Что не поможет</h2>
        <p style={{ ...P, margin: 0 }}>
          Смена Wi-Fi, перезагрузка, режим инкогнито и VPN проблему не решают:
          дело в списке доверенных центров внутри самого браузера, а не в сети.
        </p>
      </div>

      <p style={{ ...P, color: 'rgba(26,37,64,0.55)', fontSize: 13 }}>
        Не помогло? Напишите нам через форму обратной связи — подскажем и при
        необходимости выставим счёт другим способом.
      </p>
    </main>
  )
}
