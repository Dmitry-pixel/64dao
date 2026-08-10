'use client'
import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { getMe, adminApi } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

// Слотов два: Методы 1-2 продаются одним тарифом и показываются одним блоком
// лендинга, поэтому пример у них общий. У Метода 3 свой.
const SLOTS = [
  {
    method: '1',
    title: 'Методы 1 и 2',
    hint: 'Кнопки «Посмотреть пример отчёта» в первом экране и в блоке «Что в отчёте»',
    viewUrl: '/api/sample-report/view',
  },
  {
    method: '3',
    title: 'Метод 3 · Матрица силы',
    hint: 'Кнопка «Скачать пример отчёта» в блоке «Матрица силы»',
    viewUrl: '/api/sample-report/view?method=3',
  },
] as const

type Status = { uploaded: boolean; size_bytes: number | null }

function SlotCard({
  slot,
  status,
  onChanged,
  onError,
}: {
  slot: (typeof SLOTS)[number]
  status: Status | null
  onChanged: () => void
  onError: (m: string) => void
}) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.type !== 'application/pdf') {
      onError('Допускаются только PDF-файлы')
      if (fileInputRef.current) fileInputRef.current.value = ''
      return
    }
    setBusy(true)
    onError('')
    try {
      await adminApi.uploadSampleReport(file, slot.method)
      onChanged()
    } catch {
      onError(`Не удалось загрузить файл (${slot.title})`)
    } finally {
      setBusy(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleDelete = async () => {
    setBusy(true)
    onError('')
    try {
      await adminApi.deleteSampleReport(slot.method)
      onChanged()
    } catch {
      onError(`Не удалось удалить файл (${slot.title})`)
    } finally {
      setBusy(false)
    }
  }

  const uploaded = Boolean(status?.uploaded)
  const sizeLabel = status?.size_bytes ? `${(status.size_bytes / 1024 / 1024).toFixed(2)} МБ` : null

  return (
    <div style={{ maxWidth: 520, border: '1px solid rgba(26,37,64,0.09)', borderRadius: 10, padding: '24px 28px', background: 'rgba(255,255,255,0.55)' }}>
      <div style={{ fontFamily: 'Georgia,serif', fontSize: 18, color: 'var(--text)', marginBottom: 4 }}>{slot.title}</div>
      <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)', marginBottom: 18 }}>{slot.hint}</div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        <span style={{
          width: 10, height: 10, borderRadius: '50%',
          background: uploaded ? '#2e7d32' : 'rgba(26,37,64,0.25)',
          display: 'inline-block',
        }} />
        <span style={{ fontFamily: 'sans-serif', fontSize: 14, color: 'var(--text)' }}>
          {uploaded ? `Файл загружен${sizeLabel ? ` · ${sizeLabel}` : ''}` : 'Файл не загружен'}
        </span>
        {uploaded && (
          <a href={slot.viewUrl} target="_blank" rel="noreferrer" style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--red)' }}>
            открыть
          </a>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="application/pdf"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />

      <div style={{ display: 'flex', gap: 10 }}>
        <button
          className="btn btn-primary"
          style={{ padding: '9px 24px', fontSize: 13, opacity: busy ? 0.6 : 1 }}
          disabled={busy}
          onClick={() => fileInputRef.current?.click()}
        >
          {busy ? 'Загружаем…' : uploaded ? 'Заменить файл' : 'Загрузить файл'}
        </button>

        {uploaded && (
          <button
            className="btn btn-ghost"
            style={{ padding: '9px 24px', fontSize: 13, opacity: busy ? 0.6 : 1 }}
            disabled={busy}
            onClick={handleDelete}
          >
            Удалить
          </button>
        )}
      </div>
    </div>
  )
}

export default function AdminSampleReportPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [statuses, setStatuses] = useState<Record<string, Status | null>>({})
  const [error, setError] = useState('')

  const loadStatuses = () => {
    Promise.all(SLOTS.map(s => adminApi.sampleReportStatus(s.method).then(
      (d: Status) => [s.method, d] as const,
      () => [s.method, null] as const,
    )))
      .then(pairs => setStatuses(Object.fromEntries(pairs)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    getMe()
      .then(me => { if (me.role !== 'admin') router.push('/dashboard') })
      .catch(() => router.push('/login'))

    loadStatuses()
  }, [])

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>
      Загрузка…
    </div>
  )

  return (
    <>
      <AdminNav current="sample-report" />
      <div className="admin-shell">
        <AdminSide current="sample-report" />
        <div className="admin-main admin-main-pad" style={{ padding: '32px 40px' }}>

          <div style={{ marginBottom: 28 }}>
            <span className="label-red">Документы</span>
            <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: 'var(--text)', margin: '6px 0 4px' }}>
              Пример отчёта
            </h1>
            <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', margin: 0 }}>
              PDF-файлы, доступные посетителям лендинга без регистрации. По одному на тариф.
            </p>
          </div>

          {error && (
            <div style={{ marginBottom: 20, padding: '10px 16px', borderRadius: 8, background: 'rgba(192,57,43,0.08)', border: '1px solid rgba(192,57,43,0.2)', fontFamily: 'sans-serif', fontSize: 13, color: '#c0392b' }}>
              {error}
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {SLOTS.map(slot => (
              <SlotCard
                key={slot.method}
                slot={slot}
                status={statuses[slot.method] ?? null}
                onChanged={loadStatuses}
                onError={setError}
              />
            ))}
          </div>

        </div>
      </div>
    </>
  )
}
