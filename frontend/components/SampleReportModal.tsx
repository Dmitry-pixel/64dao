'use client'
import { useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || ''

type Channel = 'max' | 'telegram' | 'email'

const CHANNELS: { key: Channel; name: string; desc: string; color: string; short: string }[] = [
  { key: 'max',      name: 'Max',      desc: 'Мессенджер Max',      color: '#7c3aed', short: 'MAX' },
  { key: 'telegram', name: 'Telegram', desc: 'Отправим в Telegram', color: '#2aabee', short: 'TG' },
  { key: 'email',    name: 'E-mail',   desc: 'Пришлём на почту',    color: '#c0392b', short: '@' },
]
const PLACEHOLDER: Record<Channel, string> = {
  max: '+7 900 000-00-00',
  telegram: '@username или +7 900 000-00-00',
  email: 'you@company.ru',
}
const FIELD_LABEL: Record<Channel, string> = { max: 'Max', telegram: 'Telegram', email: 'E-mail' }

const inputStyle = {
  width: '100%', padding: '14px 16px', background: 'rgba(255,255,255,0.9)',
  border: '1px solid rgba(26,37,64,0.18)', borderRadius: 8, fontSize: 16,
  color: '#1a2540', outline: 'none', fontFamily: 'sans-serif',
}

export default function SampleReportModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [channel, setChannel] = useState<Channel | null>(null)
  const [name, setName] = useState('')
  const [address, setAddress] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!open) return null

  const reset = () => { setChannel(null); setName(''); setAddress(''); setError(null); setLoading(false) }
  const close = () => { reset(); onClose() }

  const submit = async () => {
    if (!name.trim() || !address.trim()) { setError('Заполните имя и адрес'); return }
    setError(null); setLoading(true)
    // вкладку открываем СИНХРОННО по клику — иначе браузер заблокирует popup
    const tab = window.open('about:blank', '_blank')
    try {
      const res = await fetch(`${API}/api/sample-report/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), channel, address: address.trim(), consent: true }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
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
    <div onClick={close} style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(26,37,64,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <div onClick={e => e.stopPropagation()} style={{ position: 'relative', width: 520, maxWidth: '100%', background: '#fff', borderRadius: 14, boxShadow: '0 24px 70px rgba(26,37,64,0.35)', padding: '40px 42px 34px', fontFamily: 'sans-serif' }}>
        <button onClick={close} aria-label="Закрыть" style={{ position: 'absolute', top: 18, right: 20, width: 30, height: 30, border: 'none', background: 'rgba(26,37,64,0.06)', borderRadius: '50%', fontSize: 17, color: 'rgba(26,37,64,0.6)', cursor: 'pointer' }}>×</button>

        {!channel ? (
          <>
            <span style={{ fontSize: 10, letterSpacing: 3, textTransform: 'uppercase', color: '#c0392b', fontWeight: 600 }}>Пример отчёта</span>
            <h3 style={{ fontFamily: 'Georgia,serif', fontSize: 26, fontWeight: 400, color: '#1a2540', margin: '12px 0 6px' }}>Куда отправить пример Отчёта?</h3>
            <p style={{ fontSize: 13.5, color: 'rgba(26,37,64,0.6)', margin: '0 0 26px' }}>Выберите удобный канал — вышлем PDF с примером диагностики.</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 22 }}>
              {CHANNELS.map(c => (
                <button key={c.key} onClick={() => { setChannel(c.key); setError(null) }} style={{ display: 'flex', alignItems: 'center', gap: 14, width: '100%', padding: '16px 18px', background: '#fff', border: '1px solid rgba(26,37,64,0.16)', borderRadius: 10, cursor: 'pointer', textAlign: 'left' }}>
                  <span style={{ width: 42, height: 42, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 13, color: '#fff', background: c.color }}>{c.short}</span>
                  <span style={{ flex: 1 }}>
                    <span style={{ display: 'block', fontFamily: 'Georgia,serif', fontSize: 17, color: '#1a2540', fontWeight: 600 }}>{c.name}</span>
                    <span style={{ display: 'block', fontSize: 12, color: 'rgba(26,37,64,0.4)' }}>{c.desc}</span>
                  </span>
                  <span style={{ fontSize: 18, color: 'rgba(26,37,64,0.4)' }}>→</span>
                </button>
              ))}
            </div>
            <p style={{ fontSize: 11, lineHeight: 1.6, color: 'rgba(26,37,64,0.4)' }}>
              Нажимая кнопки «Max», «Telegram» или «E-mail», Вы соглашаетесь со всеми положениями{' '}
              <a href="/documents/user-agreement" target="_blank" style={{ color: '#1e3a8a' }}>оферты</a> и даёте согласие на обработку Ваших персональных данных в соответствии с{' '}
              <a href="/documents/privacy-policy" target="_blank" style={{ color: '#1e3a8a' }}>Политикой</a>, в том числе для обработки третьими лицами и отправки рассылки.
            </p>
          </>
        ) : (
          <>
            <button onClick={() => { setChannel(null); setError(null) }} style={{ display: 'inline-flex', alignItems: 'center', gap: 7, background: 'none', border: 'none', color: 'rgba(26,37,64,0.6)', fontSize: 13, cursor: 'pointer', padding: 0, marginBottom: 20 }}>← Назад</button>
            <h3 style={{ fontFamily: 'Georgia,serif', fontSize: 26, fontWeight: 400, color: '#1a2540', margin: '0 0 6px' }}>Введите ваш {FIELD_LABEL[channel]}</h3>
            <p style={{ fontSize: 13.5, color: 'rgba(26,37,64,0.6)', margin: '0 0 22px' }}>
              Пример отчёта откроется в новой вкладке{channel === 'email' ? ' и придёт на почту' : ''}.
            </p>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 12, color: 'rgba(26,37,64,0.5)', marginBottom: 8 }}>Ваше имя</label>
              <input value={name} onChange={e => setName(e.target.value)} placeholder="Как к вам обращаться" style={inputStyle} />
            </div>
            <div style={{ marginBottom: 18 }}>
              <label style={{ display: 'block', fontSize: 12, color: 'rgba(26,37,64,0.5)', marginBottom: 8 }}>{FIELD_LABEL[channel]}</label>
              <input value={address} onChange={e => setAddress(e.target.value)} placeholder={PLACEHOLDER[channel]} style={inputStyle} />
            </div>
            {error && <p style={{ color: '#c0392b', fontSize: 12, margin: '0 0 12px' }}>{error}</p>}
            <button onClick={submit} disabled={loading} style={{ width: '100%', padding: '14px', background: '#1e3a8a', color: '#fff', border: 'none', borderRadius: 8, fontSize: 15, fontWeight: 600, cursor: loading ? 'default' : 'pointer', opacity: loading ? 0.7 : 1, marginBottom: 16 }}>
              {loading ? 'Отправляем…' : 'Получить'}
            </button>
            <p style={{ fontSize: 11, lineHeight: 1.6, color: 'rgba(26,37,64,0.4)' }}>
              Нажимая «Получить», Вы соглашаетесь с{' '}
              <a href="/documents/user-agreement" target="_blank" style={{ color: '#1e3a8a' }}>офертой</a> и{' '}
              <a href="/documents/privacy-policy" target="_blank" style={{ color: '#1e3a8a' }}>Политикой обработки ПД</a>.
            </p>
          </>
        )}
      </div>
    </div>
  )
}
