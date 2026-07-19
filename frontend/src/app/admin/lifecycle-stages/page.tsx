'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe, adminApi } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

interface Stage {
  sort_order: number
  name: string
  description: string | null
}

export default function AdminLifecycleStagesPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [stages, setStages] = useState<Stage[]>([])

  useEffect(() => {
    getMe()
      .then(me => { if (me.role !== 'admin') router.push('/dashboard') })
      .catch(() => router.push('/login'))
    adminApi.lifecycleStages()
      .then((data: any) => setStages(Array.isArray(data) ? data : []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const update = (sort: number, value: string) => {
    setSaved(false)
    setStages(prev => prev.map(s => (s.sort_order === sort ? { ...s, description: value } : s)))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await adminApi.saveLifecycleStages(
        stages.map(s => ({ sort_order: s.sort_order, description: s.description }))
      )
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

  return (
    <>
      <AdminNav current="lifecycle-stages" />
      <div className="admin-shell">
        <AdminSide current="lifecycle-stages" />
        <div className="admin-main" style={{ padding: '32px 40px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
            <div>
              <span className="label-red">Справочник</span>
              <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: 'var(--text)', margin: '6px 0 4px' }}>
                Стадии жизненного цикла
              </h1>
              <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', margin: 0, maxWidth: 560, lineHeight: 1.6 }}>
                Описание выводится в отчёте под графиком стадии. Названия не редактируются — по ним стадия связана со стратегиями.
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

          <div style={{ maxWidth: 640, display: 'flex', flexDirection: 'column', gap: 22 }}>
            {stages.map(s => (
              <div key={s.sort_order}>
                <label style={{ display: 'block', fontFamily: 'sans-serif', fontSize: 11, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', color: '#c0392b', marginBottom: 8 }}>
                  {s.sort_order}. {s.name}
                </label>
                <textarea
                  value={s.description ?? ''}
                  rows={3}
                  onChange={ev => update(s.sort_order, ev.target.value)}
                  style={{
                    width: '100%', padding: '10px 14px',
                    border: '1px solid rgba(26,37,64,0.18)', borderRadius: 8,
                    fontFamily: 'sans-serif', fontSize: 14, lineHeight: 1.6, color: 'var(--text)',
                    background: 'rgba(255,255,255,0.8)', outline: 'none',
                    boxSizing: 'border-box', resize: 'vertical',
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  )
}
