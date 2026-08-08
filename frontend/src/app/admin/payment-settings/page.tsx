'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const API = process.env.NEXT_PUBLIC_API_URL || ''

interface CreditsView {
  enforce_credits: boolean
  source: string
}

interface TochkaView {
  jwt_token_masked: string | null
  jwt_token_set: boolean
  jwt_token_source: string
  client_id_masked: string | null
  client_id_set: boolean
}

export default function AdminPaymentSettingsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [view, setView] = useState<TochkaView | null>(null)
  const [jwtInput, setJwtInput] = useState('')
  const [clientIdInput, setClientIdInput] = useState('')
  const [credits, setCredits] = useState<CreditsView | null>(null)
  const [creditsSaving, setCreditsSaving] = useState(false)

  const load = async () => {
    const res = await fetch(`${API}/api/admin/tochka-settings`, { credentials: 'include' })
    if (res.ok) setView(await res.json())
    const c = await fetch(`${API}/api/payments/admin/credits-settings`, { credentials: 'include' })
    if (c.ok) setCredits(await c.json())
  }

  useEffect(() => {
    const init = async () => {
      try {
        const me = await getMe()
        if (me.role !== 'admin') { router.push('/dashboard'); return }
        await load()
      } catch {
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  const save = async () => {
    setSaving(true)
    try {
      const res = await fetch(`${API}/api/admin/tochka-settings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ jwt_token: jwtInput, client_id: clientIdInput }),
      })
      // Та же дыра, что была в /admin/pricing: без проверки страница писала
      // «Сохранено» при любом ответе. Здесь это дороже — не записались бы
      // реквизиты платёжного шлюза. Соседний toggleCredits res.ok проверяет:
      // шаблон разошёлся внутри одного экрана.
      if (!res.ok) {
        const detail = await res.text().catch(() => '')
        alert(`Не удалось сохранить: ${res.status}. ${detail.slice(0, 300)}`)
        return
      }
      setJwtInput('')
      setClientIdInput('')
      await load()
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch {
      alert('Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  const toggleCredits = async (next: boolean) => {
    setCreditsSaving(true)
    try {
      const res = await fetch(`${API}/api/payments/admin/credits-settings?enforce_credits=${next}`, {
        method: 'PUT',
        credentials: 'include',
      })
      if (!res.ok) throw new Error()
      setCredits(await res.json())
    } catch {
      alert('Не удалось переключить')
    } finally {
      setCreditsSaving(false)
    }
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>
      Загрузка...
    </div>
  )

  const S: Record<string, React.CSSProperties> = {
    sectionTitle: { fontFamily: 'sans-serif', fontSize: 11, letterSpacing: 2, textTransform: 'uppercase', color: 'var(--text-mute)', fontWeight: 600, margin: '0 0 14px' },
    label: { display: 'block', fontFamily: 'sans-serif', fontSize: 11, color: 'var(--text-mute)', marginBottom: 5 },
    hint: { fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)', marginBottom: 8 },
    input: { width: '100%', padding: '9px 12px', border: '1px solid rgba(26,37,64,0.15)', borderRadius: 6, fontSize: 13, fontFamily: 'sans-serif', color: 'var(--dark)', background: 'rgba(255,255,255,0.8)', outline: 'none', boxSizing: 'border-box' as const },
  }

  return (
    <>
      <AdminNav current="payment-settings" />
      <div className="admin-shell">
        <AdminSide current="payment-settings" />
        <div className="admin-main admin-main-pad" style={{ padding: '32px 40px' }}>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28, flexWrap: 'wrap', gap: 16 }}>
            <div>
              <span className="label-red">Система</span>
              <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: 'var(--dark)', margin: '6px 0 0' }}>Настройка оплаты</h1>
            </div>
            <button onClick={save} disabled={saving} style={{ background: saved ? '#166534' : 'var(--dark)', color: '#fff', border: 'none', borderRadius: 6, padding: '10px 24px', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer', fontWeight: 500, minWidth: 140 }}>
              {saving ? 'Сохраняем...' : saved ? 'Сохранено' : 'Сохранить'}
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 640 }}>

            <div className="card" style={{ padding: '20px 24px' }}>
              <h3 style={S.sectionTitle}>Обязательная оплата диагностик</h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
                <button
                  onClick={() => toggleCredits(!credits?.enforce_credits)}
                  disabled={creditsSaving || !credits}
                  style={{
                    background: credits?.enforce_credits ? '#166534' : 'rgba(26,37,64,0.12)',
                    color: credits?.enforce_credits ? '#fff' : 'var(--dark)',
                    border: 'none', borderRadius: 6, padding: '10px 22px',
                    fontFamily: 'sans-serif', fontSize: 13, fontWeight: 500,
                    cursor: creditsSaving ? 'default' : 'pointer', minWidth: 150,
                  }}>
                  {creditsSaving ? 'Сохраняем...' : credits?.enforce_credits ? 'Включена' : 'Выключена'}
                </button>
                <span style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)' }}>
                  {credits ? (credits.source === 'admin' ? 'значение задано здесь' : 'значение из .env на сервере') : ''}
                </span>
              </div>
              <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)', marginTop: 14, lineHeight: 1.5 }}>
                Когда включена: завершённая диагностика требует оплаченного кредита или гранта,
                а результат диагностики в статусе «черновик» закрыт. Администратора ограничение не касается.
                Переключение действует сразу, без перезапуска backend — это аварийный выключатель,
                поэтому сохраняется по клику, отдельно от кнопки «Сохранить» выше.
              </div>
            </div>

            <div className="card" style={{ padding: '20px 24px' }}>
              <h3 style={S.sectionTitle}>Точка Банк — доступ к API</h3>

              <label style={S.label}>Client ID</label>
              <div style={S.hint}>
                {view?.client_id_set
                  ? `Сейчас сохранён: ${view.client_id_masked}`
                  : 'Не задан.'}
              </div>
              <input
                style={S.input}
                placeholder="Оставьте пустым, чтобы не менять"
                value={clientIdInput}
                onChange={e => setClientIdInput(e.target.value)}
              />

              <label style={{ ...S.label, marginTop: 18 }}>JWT-токен</label>
              <div style={S.hint}>
                {view?.jwt_token_set
                  ? `Сейчас используется: ${view.jwt_token_masked} (источник: ${view.jwt_token_source === 'admin' ? 'сохранён здесь' : '.env на сервере'})`
                  : 'Не задан.'}
              </div>
              <textarea
                style={{ ...S.input, height: 90, resize: 'vertical' as const, fontFamily: 'monospace', fontSize: 11 }}
                placeholder="Оставьте пустым, чтобы не менять"
                value={jwtInput}
                onChange={e => setJwtInput(e.target.value)}
              />

              <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)', marginTop: 14, lineHeight: 1.5 }}>
                Токен выпускается в личном кабинете Точки: Сервисы → Интеграции и API → Сгенерировать JWT-токен.
                Client ID — тот же, что указан в claim <code>iss</code> внутри токена.
                Изменения применяются сразу, без пересборки backend.
              </div>
            </div>

          </div>
        </div>
      </div>
    </>
  )
}
