'use client'
import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { getMe, adminApi } from '@/lib/api'
import type { LogEntry } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const TYPE_META: Record<string, { label: string; color: string; bg: string; icon: string }> = {
  user:       { label: 'Регистрация',  color: '#1e7e34', bg: 'rgba(30,126,52,0.1)',   icon: '👤' },
  assessment: { label: 'Диагностика', color: '#1e3a8a', bg: 'rgba(30,58,138,0.1)',   icon: '📊' },
  report:     { label: 'PDF',          color: '#c0392b', bg: 'rgba(192,57,43,0.1)',   icon: '📄' },
}

function formatTs(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export default function AdminLogsPage() {
  const router = useRouter()
  const [entries, setEntries] = useState<LogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [resetting, setResetting] = useState(false)
  const [total, setTotal] = useState(0)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await adminApi.logs() as LogEntry[]
      setEntries(data)
      setTotal(data.length)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    getMe()
      .then(me => { if (me.role !== 'admin') router.push('/dashboard') })
      .catch(() => router.push('/login'))
      .then(() => load())
  }, [])

  const handleReset = async () => {
    setResetting(true)
    setEntries([])
    setTotal(0)
    await new Promise(r => setTimeout(r, 300))
    await load()
    setResetting(false)
  }

  const counts = {
    user:       entries.filter(e => e.type === 'user').length,
    assessment: entries.filter(e => e.type === 'assessment').length,
    report:     entries.filter(e => e.type === 'report').length,
  }

  return (
    <>
      <AdminNav current="logs" />
      <div className="admin-shell">
        <AdminSide current="logs" />
        <div className="admin-main" style={{ padding: '32px 40px' }}>

          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
            <div>
              <span className="label-red">Система</span>
              <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: 'var(--text)', margin: '6px 0 4px' }}>
                Логи
              </h1>
              <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)', margin: 0 }}>
                {loading
                  ? 'Загружаем события…'
                  : `Последние ${total} событий · ${counts.user} регистр. · ${counts.assessment} диагн. · ${counts.report} PDF`}
              </p>
            </div>
            <button
              className="btn btn-ghost"
              style={{ padding: '9px 20px', fontSize: 13 }}
              disabled={loading || resetting}
              onClick={handleReset}
            >
              {resetting ? 'Сброс…' : '↺ Сбросить'}
            </button>
          </div>

          {/* Legend */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
            {Object.entries(TYPE_META).map(([type, meta]) => (
              <div key={type} style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '4px 12px', borderRadius: 20,
                background: meta.bg, border: `1px solid ${meta.color}22`,
                fontFamily: 'sans-serif', fontSize: 12, color: meta.color, fontWeight: 600,
              }}>
                <span>{meta.icon}</span>
                <span>{meta.label}</span>
                <span style={{ opacity: 0.6, fontWeight: 400 }}>·</span>
                <span>{counts[type as keyof typeof counts]}</span>
              </div>
            ))}
          </div>

          {/* Feed */}
          {loading ? (
            <div style={{ padding: '48px 0', textAlign: 'center', fontFamily: 'sans-serif', fontSize: 14, color: 'var(--text-mute)' }}>
              Загрузка…
            </div>
          ) : entries.length === 0 ? (
            <div className="dash-empty">
              <span style={{ fontSize: 40, display: 'block', marginBottom: 12 }}>📋</span>
              <h3>Событий пока нет</h3>
              <p>Здесь появятся регистрации пользователей, диагностики и PDF-отчёты.</p>
            </div>
          ) : (
            <div style={{
              border: '1px solid rgba(26,37,64,0.09)',
              borderRadius: 10,
              overflow: 'hidden',
              background: 'rgba(255,255,255,0.55)',
            }}>
              {entries.map((entry, i) => {
                const meta = TYPE_META[entry.type] ?? TYPE_META.user
                const isLast = i === entries.length - 1
                return (
                  <div
                    key={i}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '36px 1fr auto',
                      alignItems: 'center',
                      gap: 14,
                      padding: '12px 20px',
                      borderBottom: isLast ? 'none' : '1px solid rgba(26,37,64,0.06)',
                      background: i % 2 === 0 ? 'transparent' : 'rgba(26,37,64,0.015)',
                    }}
                  >
                    {/* Icon */}
                    <div style={{
                      width: 32, height: 32, borderRadius: '50%',
                      background: meta.bg,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 14, flexShrink: 0,
                    }}>
                      {meta.icon}
                    </div>

                    {/* Content */}
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                        <span style={{
                          fontFamily: 'sans-serif', fontSize: 11, fontWeight: 700,
                          letterSpacing: 1, textTransform: 'uppercase',
                          color: meta.color,
                        }}>{meta.label}</span>
                        {entry.sub && (
                          <span style={{
                            fontFamily: 'monospace', fontSize: 12,
                            color: 'rgba(26,37,64,0.45)',
                            background: 'rgba(26,37,64,0.06)',
                            padding: '1px 7px', borderRadius: 4,
                          }}>{entry.sub}</span>
                        )}
                      </div>
                      <div style={{ fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text)' }}>
                        {entry.user_name
                          ? <><strong>{entry.user_name}</strong> <span style={{ color: 'var(--text-mute)' }}>· {entry.user_email}</span></>
                          : <span>{entry.user_email}</span>
                        }
                      </div>
                    </div>

                    {/* Timestamp */}
                    <div style={{
                      fontFamily: 'sans-serif', fontSize: 12,
                      color: 'rgba(26,37,64,0.4)',
                      whiteSpace: 'nowrap', textAlign: 'right',
                    }}>
                      {formatTs(entry.timestamp)}
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Footer note */}
          {!loading && entries.length > 0 && (
            <p style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.35)', marginTop: 14, textAlign: 'center' }}>
              Показано {entries.length} из последних 100 событий.
              Нажмите «↺ Сбросить» чтобы обновить ленту.
            </p>
          )}

        </div>
      </div>
    </>
  )
}
