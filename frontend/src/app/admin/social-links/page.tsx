'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe, adminApi } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

interface SocialLinks {
  telegram: string
  vk: string
  max: string
}

export default function AdminSocialLinksPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [links, setLinks] = useState<SocialLinks>({ telegram: '', vk: '', max: '' })

  useEffect(() => {
    getMe()
      .then(me => { if (me.role !== 'admin') router.push('/dashboard') })
      .catch(() => router.push('/login'))

    adminApi.socialLinks()
      .then((data: any) => setLinks(data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const update = (field: keyof SocialLinks, value: string) => {
    setSaved(false)
    setLinks(prev => ({ ...prev, [field]: value }))
  }

  const clear = (field: keyof SocialLinks) => update(field, '')

  const handleSave = async () => {
    setSaving(true)
    try {
      await adminApi.saveSocialLinks(links)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch {
      alert('Не удалось сохранить. Попробуйте ещё раз.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>
      Загрузка…
    </div>
  )

  const fields: { key: keyof SocialLinks; label: string; placeholder: string }[] = [
    { key: 'telegram', label: 'Telegram', placeholder: 'https://t.me/...' },
    { key: 'vk',       label: 'VK',       placeholder: 'https://vk.com/...' },
    { key: 'max',      label: 'Max',      placeholder: 'https://max.ru/...' },
  ]

  return (
    <>
      <AdminNav current="social-links" />
      <div className="admin-shell">
        <AdminSide current="social-links" />
        <div className="admin-main admin-main-pad" style={{ padding: '32px 40px' }}>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28, flexWrap: 'wrap', gap: 16 }}>
            <div>
              <span className="label-red">Система</span>
              <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: 'var(--text)', margin: '6px 0 4px' }}>
                Соц. сети
              </h1>
              <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', margin: 0 }}>
                Адреса, на которые ведут иконки соц.сетей на лендинге
              </p>
            </div>
            <button
              className={`btn ${saved ? 'btn-ghost' : 'btn-primary'}`}
              style={{ padding: '9px 24px', fontSize: 13, opacity: saving ? 0.6 : 1 }}
              disabled={saving}
              onClick={handleSave}
            >
              {saving ? 'Сохраняем…' : saved ? '✓ Сохранено' : 'Сохранить'}
            </button>
          </div>

          <div style={{ maxWidth: 480, display: 'flex', flexDirection: 'column', gap: 20 }}>
            {fields.map(f => (
              <div key={f.key}>
                <label style={{ display: 'block', fontFamily: 'sans-serif', fontSize: 11, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', color: '#c0392b', marginBottom: 8 }}>
                  {f.label}
                </label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    type="text"
                    value={links[f.key]}
                    placeholder={f.placeholder}
                    onChange={e => update(f.key, e.target.value)}
                    style={{
                      flex: 1, padding: '10px 14px',
                      border: '1px solid rgba(26,37,64,0.18)', borderRadius: 8,
                      fontFamily: 'sans-serif', fontSize: 14, color: 'var(--text)',
                      background: 'rgba(255,255,255,0.8)', outline: 'none', boxSizing: 'border-box',
                    }}
                  />
                  {links[f.key] && (
                    <button
                      onClick={() => clear(f.key)}
                      title="Удалить адрес"
                      style={{
                        padding: '0 14px', border: '1px solid rgba(26,37,64,0.18)', borderRadius: 8,
                        background: 'rgba(255,255,255,0.6)', cursor: 'pointer',
                        fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)',
                      }}
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

        </div>
      </div>
    </>
  )
}
