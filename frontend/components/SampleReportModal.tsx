'use client'
import { useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || ''

/**
 * Форма перед скачиванием документа.
 *
 * До этого форма спрашивала один канал на выбор и один адрес. Так контакт
 * приходил ровно один, а связаться потом было нечем: половина лидов оставляла
 * @username без телефона. Теперь имя, e-mail и телефон обязательны,
 * мессенджеры — по желанию.
 *
 * method определяет, какой PDF откроется и в какой сегмент попадёт лид:
 * '1' — пример Методов 1-2, '3' — пример Метода 3, 'methodology' — методика.
 */
export type SampleDoc = '1' | '3' | 'methodology'

const DOC_TEXT: Record<SampleDoc, { label: string; title: string; hint: string }> = {
  '1': {
    label: 'Пример отчёта',
    title: 'Куда отправить пример отчёта?',
    hint: 'Пример откроется в новой вкладке и придёт на почту.',
  },
  '3': {
    label: 'Пример отчёта · Метод 3',
    title: 'Куда отправить пример отчёта?',
    hint: 'Пример откроется в новой вкладке и придёт на почту.',
  },
  methodology: {
    label: 'Методика 64DAO',
    title: 'Куда отправить методику?',
    hint: 'Описание методологии откроется в новой вкладке и придёт на почту.',
  },
}

const inputStyle = {
  width: '100%', padding: '13px 16px', background: 'rgba(255,255,255,0.9)',
  border: '1px solid rgba(26,37,64,0.18)', borderRadius: 8, fontSize: 16,
  color: '#1a2540', outline: 'none', fontFamily: 'sans-serif',
} as const

const labelStyle = {
  display: 'block', fontSize: 12, color: 'rgba(26,37,64,0.5)', marginBottom: 7,
} as const

function Field({
  label, value, onChange, placeholder, type = 'text', optional = false,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder: string
  type?: string
  optional?: boolean
}) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={labelStyle}>
        {label}
        {optional && <span style={{ color: 'rgba(26,37,64,0.3)' }}> · необязательно</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        style={inputStyle}
      />
    </div>
  )
}

export default function SampleReportModal({
  open,
  onClose,
  method = '1',
}: {
  open: boolean
  onClose: () => void
  method?: SampleDoc
}) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [maxAddress, setMaxAddress] = useState('')
  const [telegram, setTelegram] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  if (!open) return null

  const text = DOC_TEXT[method]

  const reset = () => {
    setName(''); setEmail(''); setPhone(''); setMaxAddress(''); setTelegram('')
    setError(null); setLoading(false); setDone(false)
  }
  const close = () => { reset(); onClose() }

  const submit = async () => {
    if (!name.trim())  { setError('Укажите имя'); return }
    if (!email.trim()) { setError('Укажите e-mail'); return }
    if (!phone.trim()) { setError('Укажите телефон'); return }
    setError(null); setLoading(true)
    // Вкладку открываем СИНХРОННО по клику — иначе браузер заблокирует popup.
    const tab = window.open('about:blank', '_blank')
    try {
      const res = await fetch(`${API}/api/sample-report/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          phone: phone.trim(),
          max_address: maxAddress.trim() || null,
          telegram_address: telegram.trim() || null,
          method,
          consent: true,
        }),
      })
      // 429 приходит от лимитера по IP. Раньше он падал в общий catch и
      // человек видел «попробуйте ещё раз» — пробовал, получал то же самое
      // и уходил. Сообщение должно называть причину, иначе повтор бесполезен.
      if (res.status === 429) {
        if (tab) tab.close()
        setError('Слишком много запросов с вашего адреса. Попробуйте через минуту.')
        setLoading(false)
        return
      }
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      // Файл могли ещё не загрузить в админку: контакт при этом сохранён,
      // открывать пустую вкладку незачем — показываем честное сообщение.
      if (!data.pdf_url) {
        if (tab) tab.close()
        setLoading(false)
        setDone(true)
        return
      }
      const url = `${API}${data.pdf_url}`
      if (tab) tab.location.href = url
      else window.location.href = url
      close()
    } catch {
      if (tab) tab.close()
      setError('Не удалось отправить. Попробуйте ещё раз.')
      setLoading(false)
    }
  }

  return (
    <div onClick={close} style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(26,37,64,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16, overflowY: 'auto' }}>
      <div onClick={e => e.stopPropagation()} style={{ position: 'relative', width: 520, maxWidth: '100%', background: '#fff', borderRadius: 14, boxShadow: '0 24px 70px rgba(26,37,64,0.35)', padding: '38px 42px 32px', fontFamily: 'sans-serif', margin: 'auto' }}>
        <button onClick={close} aria-label="Закрыть" style={{ position: 'absolute', top: 18, right: 20, width: 30, height: 30, border: 'none', background: 'rgba(26,37,64,0.06)', borderRadius: '50%', fontSize: 17, color: 'rgba(26,37,64,0.6)', cursor: 'pointer' }}>×</button>

        <span style={{ fontSize: 10, letterSpacing: 3, textTransform: 'uppercase', color: '#c0392b', fontWeight: 600 }}>{text.label}</span>

        {done ? (
          <>
            <h3 style={{ fontFamily: 'Georgia,serif', fontSize: 24, fontWeight: 400, color: '#1a2540', margin: '12px 0 8px' }}>Спасибо, контакты сохранены</h3>
            <p style={{ fontSize: 13.5, lineHeight: 1.6, color: 'rgba(26,37,64,0.6)', margin: '0 0 22px' }}>
              Документ сейчас обновляется. Мы пришлём его на указанный e-mail, как только он будет готов.
            </p>
            <button onClick={close} style={{ width: '100%', padding: '13px', background: '#1e3a8a', color: '#fff', border: 'none', borderRadius: 8, fontSize: 15, fontWeight: 600, cursor: 'pointer' }}>
              Закрыть
            </button>
          </>
        ) : (
          <>
            <h3 style={{ fontFamily: 'Georgia,serif', fontSize: 25, fontWeight: 400, color: '#1a2540', margin: '12px 0 6px' }}>{text.title}</h3>
            <p style={{ fontSize: 13.5, color: 'rgba(26,37,64,0.6)', margin: '0 0 22px' }}>{text.hint}</p>

            <Field label="Ваше имя"  value={name}       onChange={setName}       placeholder="Как к вам обращаться" />
            <Field label="E-mail"    value={email}      onChange={setEmail}      placeholder="you@company.ru" type="email" />
            <Field label="Телефон"   value={phone}      onChange={setPhone}      placeholder="+7 900 000-00-00" type="tel" />
            <Field label="Max"       value={maxAddress} onChange={setMaxAddress} placeholder="+7 900 000-00-00" optional />
            <Field label="Telegram"  value={telegram}   onChange={setTelegram}   placeholder="@username" optional />

            {error && <p style={{ color: '#c0392b', fontSize: 12, margin: '4px 0 12px' }}>{error}</p>}

            <button onClick={submit} disabled={loading} style={{ width: '100%', padding: '14px', background: '#1e3a8a', color: '#fff', border: 'none', borderRadius: 8, fontSize: 15, fontWeight: 600, cursor: loading ? 'default' : 'pointer', opacity: loading ? 0.7 : 1, margin: '8px 0 16px' }}>
              {loading ? 'Отправляем…' : 'Получить'}
            </button>

            <p style={{ fontSize: 11, lineHeight: 1.6, color: 'rgba(26,37,64,0.4)', margin: 0 }}>
              Нажимая «Получить», Вы соглашаетесь со всеми положениями{' '}
              <a href="/documents/user-agreement" target="_blank" style={{ color: '#1e3a8a' }}>оферты</a> и даёте согласие на обработку Ваших персональных данных в соответствии с{' '}
              <a href="/documents/privacy-policy" target="_blank" style={{ color: '#1e3a8a' }}>Политикой</a>, в том числе для обработки третьими лицами и отправки рассылки.
            </p>
          </>
        )}
      </div>
    </div>
  )
}
