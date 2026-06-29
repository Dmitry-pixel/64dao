'use client'
import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { getMe, adminApi } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

export default function AdminSampleReportPage() {
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(true)
  const [uploaded, setUploaded] = useState(false)
  const [sizeBytes, setSizeBytes] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadStatus = () => {
    adminApi.sampleReportStatus()
      .then((data: any) => {
        setUploaded(data.uploaded)
        setSizeBytes(data.size_bytes)
      })
      .catch(() => setError('Не удалось получить статус файла'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    getMe()
      .then(me => { if (me.role !== 'admin') router.push('/dashboard') })
      .catch(() => router.push('/login'))

    loadStatus()
  }, [])

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.type !== 'application/pdf') {
      setError('Допускаются только PDF-файлы')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await adminApi.uploadSampleReport(file)
      loadStatus()
    } catch {
      setError('Не удалось загрузить файл')
    } finally {
      setBusy(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleDelete = async () => {
    setBusy(true)
    setError(null)
    try {
      await adminApi.deleteSampleReport()
      setUploaded(false)
      setSizeBytes(null)
    } catch {
      setError('Не удалось удалить файл')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>
      Загрузка…
    </div>
  )

  const sizeLabel = sizeBytes ? `${(sizeBytes / 1024 / 1024).toFixed(2)} МБ` : null

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
              PDF-файл, доступный для скачивания всем посетителям лендинга без регистрации
            </p>
          </div>

          {error && (
            <div style={{ marginBottom: 20, padding: '10px 16px', borderRadius: 8, background: 'rgba(192,57,43,0.08)', border: '1px solid rgba(192,57,43,0.2)', fontFamily: 'sans-serif', fontSize: 13, color: '#c0392b' }}>
              {error}
            </div>
          )}

          <div style={{ maxWidth: 480, border: '1px solid rgba(26,37,64,0.09)', borderRadius: 10, padding: '24px 28px', background: 'rgba(255,255,255,0.55)' }}>

            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
              <span style={{
                width: 10, height: 10, borderRadius: '50%',
                background: uploaded ? '#2e7d32' : 'rgba(26,37,64,0.25)',
                display: 'inline-block',
              }} />
              <span style={{ fontFamily: 'sans-serif', fontSize: 14, color: 'var(--text)' }}>
                {uploaded ? `Файл загружен${sizeLabel ? ` · ${sizeLabel}` : ''}` : 'Файл не загружен'}
              </span>
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

        </div>
      </div>
    </>
  )
}
