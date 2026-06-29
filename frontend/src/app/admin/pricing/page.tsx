'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const API = process.env.NEXT_PUBLIC_API_URL || ''

interface Feature { label: string; value: string }
interface PricingConfig {
  title: string
  price: number
  currency: string
  description: string
  features: Feature[]
  payment_enabled: boolean
  payment_note: string
}

const DEFAULT: PricingConfig = {
  title: 'Полный отчёт 64 ДАО',
  price: 14900,
  currency: '₽',
  description: 'разовая оплата · НДС не облагается',
  features: [
    { label: 'Диагностика', value: 'Метод 1 + Метод 2' },
    { label: 'PDF-отчёт', value: 'Включён' },
    { label: 'Онлайн-просмотр', value: 'Без ограничений' },
    { label: 'Срок готовности', value: 'До 30 минут' },
  ],
  payment_enabled: false,
  payment_note: 'Платёжный шлюз (ЮKassa / Тинькофф) подключим после тестирования сайта. Пока что отчёты доступны в демо-режиме без оплаты.',
}

export default function AdminPricingPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [cfg, setCfg] = useState<PricingConfig>(DEFAULT)

  useEffect(() => {
    const init = async () => {
      try {
        const me = await getMe()
        if (me.role !== 'admin') { router.push('/dashboard'); return }
        const res = await fetch(`${API}/api/admin/pricing`, { credentials: 'include' })
        if (res.ok) setCfg(await res.json())
      } catch {
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  const set = (key: keyof PricingConfig, value: any) =>
    setCfg(prev => ({ ...prev, [key]: value }))

  const setFeature = (i: number, field: keyof Feature, value: string) =>
    setCfg(prev => ({
      ...prev,
      features: prev.features.map((f, idx) => idx === i ? { ...f, [field]: value } : f),
    }))

  const addFeature = () =>
    setCfg(prev => ({ ...prev, features: [...prev.features, { label: '', value: '' }] }))

  const removeFeature = (i: number) =>
    setCfg(prev => ({ ...prev, features: prev.features.filter((_, idx) => idx !== i) }))

  const save = async () => {
    setSaving(true)
    try {
      await fetch(`${API}/api/admin/pricing`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(cfg),
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch {
      alert('Ошибка сохранения')
    } finally {
      setSaving(false)
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
    input: { width: '100%', padding: '9px 12px', border: '1px solid rgba(26,37,64,0.15)', borderRadius: 6, fontSize: 13, fontFamily: 'sans-serif', color: 'var(--text)', background: 'rgba(255,255,255,0.8)', outline: 'none', boxSizing: 'border-box' as const },
    btnGhost: { background: 'none', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6, padding: '8px 16px', fontFamily: 'sans-serif', cursor: 'pointer', color: 'var(--text)' },
    preview: { background: '#fff', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 12, padding: '28px 24px', display: 'flex', flexDirection: 'column' as const },
    previewEyebrow: { fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 3, textTransform: 'uppercase' as const, color: 'rgba(26,37,64,0.4)', textAlign: 'center' as const, marginBottom: 10 },
    previewTitle: { fontFamily: 'Georgia,serif', fontSize: 22, fontWeight: 400, color: '#1a2540', textAlign: 'center' as const, margin: '0 0 14px' },
    previewPrice: { fontFamily: 'Georgia,serif', fontSize: 44, fontWeight: 400, color: '#1a2540', textAlign: 'center' as const, lineHeight: 1, marginBottom: 6 },
    previewDesc: { fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.45)', textAlign: 'center' as const, marginBottom: 16 },
    previewDivider: { height: 1, background: 'rgba(26,37,64,0.08)', margin: '10px 0' },
    previewRow: { display: 'flex', justifyContent: 'space-between', fontFamily: 'sans-serif', fontSize: 13, color: '#1a2540', padding: '7px 0' },
    previewBtn: { background: '#3d4a6b', color: '#fff', border: 'none', borderRadius: 8, padding: '14px', fontFamily: 'sans-serif', fontSize: 14, fontWeight: 500, width: '100%', marginTop: 16, textAlign: 'center' as const },
    previewNote: { background: '#fff5f5', border: '1px solid rgba(192,57,43,0.2)', borderRadius: 8, padding: '12px 14px', marginTop: 10, fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.7)', lineHeight: 1.5 },
    previewBack: { background: 'none', border: '1px solid rgba(26,37,64,0.15)', borderRadius: 8, padding: '11px', fontFamily: 'sans-serif', fontSize: 13, color: '#1a2540', width: '100%', marginTop: 10, cursor: 'pointer', textAlign: 'center' as const },
  }

  return (
    <>
      <AdminNav current="pricing" />
      <div className="admin-shell">
        <AdminSide current="pricing" />
        <div className="admin-main admin-main-pad" style={{ padding: '32px 40px' }}>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28, flexWrap: 'wrap', gap: 16 }}>
            <div>
              <span className="label-red">Система</span>
              <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: 'var(--text)', margin: '6px 0 0' }}>Тариф &amp; Цена</h1>
            </div>
            <button onClick={save} disabled={saving} style={{ background: saved ? '#166534' : 'var(--text)', color: '#fff', border: 'none', borderRadius: 6, padding: '10px 24px', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer', fontWeight: 500, minWidth: 140 }}>
              {saving ? 'Сохраняем...' : saved ? 'Сохранено' : 'Сохранить'}
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 720 }}>

            <div className="card" style={{ padding: '20px 24px' }}>
              <h3 style={S.sectionTitle}>Основное</h3>
              <label style={S.label}>Заголовок</label>
              <input style={S.input} value={cfg.title} onChange={e => set('title', e.target.value)} />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 80px', gap: 12, marginTop: 14 }}>
                <div>
                  <label style={S.label}>Цена (цифры)</label>
                  <input style={S.input} type="number" value={cfg.price} onChange={e => set('price', Number(e.target.value))} />
                </div>
                <div>
                  <label style={S.label}>Валюта</label>
                  <input style={S.input} value={cfg.currency} onChange={e => set('currency', e.target.value)} />
                </div>
              </div>
              <label style={{ ...S.label, marginTop: 14 }}>Подпись под ценой</label>
              <input style={S.input} value={cfg.description} onChange={e => set('description', e.target.value)} />
            </div>

            <div className="card" style={{ padding: '20px 24px' }}>
              <h3 style={S.sectionTitle}>Характеристики</h3>
              {cfg.features.map((f, i) => (
                <div key={i} className="admin-pricing-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 32px', gap: 10, marginBottom: 10, alignItems: 'center' }}>
                  <input style={S.input} placeholder="Название" value={f.label} onChange={e => setFeature(i, 'label', e.target.value)} />
                  <input style={S.input} placeholder="Значение" value={f.value} onChange={e => setFeature(i, 'value', e.target.value)} />
                  <button onClick={() => removeFeature(i)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#c0392b', fontSize: 18, lineHeight: 1 }}>x</button>
                </div>
              ))}
              <button onClick={addFeature} style={{ ...S.btnGhost, marginTop: 4, fontSize: 12 }}>+ Добавить строку</button>
            </div>

            <div className="card" style={{ padding: '20px 24px' }}>
              <h3 style={S.sectionTitle}>Статус оплаты</h3>
              <label style={{ display: 'flex', alignItems: 'center', gap: 10, fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text)', cursor: 'pointer', marginBottom: 14 }}>
                <input type="checkbox" checked={cfg.payment_enabled} onChange={e => set('payment_enabled', e.target.checked)} style={{ width: 16, height: 16 }} />
                Оплата включена (кнопка активна)
              </label>
              <label style={S.label}>Текст заглушки</label>
              <textarea style={{ ...S.input, height: 80, resize: 'vertical' as const }} value={cfg.payment_note} onChange={e => set('payment_note', e.target.value)} />
            </div>

            <div>
              <div style={{ fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 2, textTransform: 'uppercase', color: 'var(--text-mute)', marginBottom: 12 }}>Превью</div>
              <div style={{ ...S.preview, maxWidth: 440 }}>
                <div style={S.previewEyebrow}>ОПЛАТА ДИАГНОСТИКИ</div>
                <h2 style={S.previewTitle}>{cfg.title || '—'}</h2>
                <div style={S.previewPrice}>{cfg.price.toLocaleString('ru-RU')} <span style={{ fontSize: 28 }}>{cfg.currency}</span></div>
                <div style={S.previewDesc}>{cfg.description}</div>
                <div style={S.previewDivider} />
                {cfg.features.map((f, i) => (
                  <div key={i} style={S.previewRow}><span>{f.label}</span><span style={{ fontWeight: 500 }}>{f.value}</span></div>
                ))}
                <div style={S.previewDivider} />
                <button style={{ ...S.previewBtn, opacity: cfg.payment_enabled ? 1 : 0.5 }}>Перейти к оплате →</button>
                {!cfg.payment_enabled && cfg.payment_note && (
                  <div style={S.previewNote}>
                    <div style={{ fontWeight: 600, color: '#c0392b', marginBottom: 4, fontSize: 12 }}>Заглушка · оплата временно отключена</div>
                    <div>{cfg.payment_note}</div>
                  </div>
                )}
                <button style={S.previewBack}>← Вернуться в кабинет</button>
              </div>
            </div>

          </div>
        </div>
      </div>
    </>
  )
}
