'use client'
import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { getMe, adminApi } from '@/lib/api'
import type { LogEntry } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const RESET_KEY = 'logsResetAt'

const TYPE_META: Record<string, { label: string; color: string; bg: string; icon: string }> = {
  user:       { label: 'Регистрация',  color: '#1e7e34', bg: 'rgba(30,126,52,0.1)',  icon: '👤' },
  assessment: { label: 'Диагностика', color: '#1e3a8a', bg: 'rgba(30,58,138,0.1)',  icon: '📊' },
  report:     { label: 'PDF',          color: '#c0392b', bg: 'rgba(192,57,43,0.1)',  icon: '📄' },
}

function formatTs(iso: string): string {
  return new Date(iso).toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatResetTime(iso: string): string {
  return new Date(iso).toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

export default function AdminLogsPage() {
  const router = useRouter()
  const [entries, setEntries] = useState<LogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [resetAt, setResetAt] = useState<string | null>(null)

  const load = useCallback(async (reset?: string) => {
    setLoading(true)
    try {
      const all = await adminApi.logs() as LogEntry[]
      const cutoff = reset ?? (typeof window !== 'undefined' ? localStorage.getItem(RESET_KEY) : null)
      const filtered = cutoff ? all.filter(e => e.timestamp > cutoff) : all
      setEntries(filtered)
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

    const stored = typeof window !== 'undefined' ? localStorage.getItem(RESET_KEY) : null
    if (stored) setResetAt(stored)
    load(stored ?? undefined)
  }, [])

  const handleReset = () => {
    const now = new Date().toISOString()
    localStorage.setItem(RESET_KEY, now)
    setResetAt(now)
    setEntries([])
  }

  const handleRefresh = () => {
    const cutoff = typeof window !== 'undefined' ? localStorage.getItem(RESET_KEY) : null
    load(cutoff ?? undefined)
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
                  : resetAt
                    ? `События после ${formatResetTime(resetAt)} · ${entries.length} новых`
                    : `Последние ${entries.length} событий · ${counts.user} регистр. · ${counts.assessment} диагн. · ${counts.report} PDF`}
              </p>
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <button
                className="btn btn-ghost"
                style={{ padding: '9px 20px', fontSize: 13 }}
                disabled={loading}
                onClick={handleRefresh}
              >
                ↺ Обновить
              </button>
              <button
                className="btn btn-ghost"
                style={{ padding: '9px 20px', fontSize: 13, color: '#c0392b', borderColor: 'rgba(192,57,43,0.25)' }}
                disabled={loading}
                onClick={handleReset}
              >
                Сбросить
              </button>
            </div>
          </div>

          {/* Reset notice */}
          {resetAt && (
            <div style={{
              marginBottom: 20, padding: '10px 16px', borderRadius: 8,
              background: 'rgba(192,57,43,0.06)', border: '1px solid rgba(192,57,43,0.2)',
              fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.65)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <span>Сброс выполнен {formatResetTime(resetAt)}. Показаны только новые события после этой отметки.</span>
              <button
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'sans-serif', fontSize: 12, color: '#c0392b' }}
                onClick={() => {
                  localStorage.removeItem(RESET_KEY)
                  setResetAt(null)
                  load()
                }}
              >
                Показать все
              </button>
            </div>
          )}

          {/* Legend */}
          {!loading && entries.length > 0 && (
            <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
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
          )}

          {/* Feed */}
          {loading ? (
            <div style={{ padding: '48px 0', textAlign: 'center', fontFamily: 'sans-serif', fontSize: 14, color: 'var(--text-mute)' }}>
              Загрузка…
            </div>
          ) : entries.length === 0 ? (
            <div className="dash-empty">
              <span style={{ fontSize: 40, display: 'block', marginBottom: 12 }}>📋</span>
              <h3>{resetAt ? 'Новых событий пока нет' : 'Событий пока нет'}</h3>
              <p>{resetAt
                ? 'После сброса новых регистраций, диагностик и PDF не было. Нажмите «Обновить» чтобы проверить снова.'
                : 'Здесь появятся регистрации пользователей, диагностики и PDF-отчёты.'
              }</p>
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
                    <div style={{
                      width: 32, height: 32, borderRadius: '50%',
                      background: meta.bg,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 14, flexShrink: 0,
                    }}>
                      {meta.icon}
                    </div>

                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                        <span style={{
                          fontFamily: 'sans-serif', fontSize: 11, fontWeight: 700,
                          letterSpacing: 1, textTransform: 'uppercase', color: meta.color,
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

          {!loading && entries.length > 0 && (
            <p style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.35)', marginTop: 14, textAlign: 'center' }}>
              Показано {entries.length} событий.
            </p>
          )}

        </div>
      </div>
    </>
  )
}
