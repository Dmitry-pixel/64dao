'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { adminApi, ImpersonateStatus } from '@/lib/api'

export function ImpersonationBanner() {
  const router = useRouter()
  const [status, setStatus] = useState<ImpersonateStatus | null>(null)
  const [stopping, setStopping] = useState(false)

  useEffect(() => {
    adminApi.impersonateStatus()
      .then(setStatus)
      .catch(() => {/* не авторизован — молчим */})
  }, [])

  if (!status?.active) return null

  const name = status.target_user?.full_name ?? status.target_user?.email ?? 'пользователя'

  async function handleStop() {
    setStopping(true)
    try {
      await adminApi.stopImpersonate()
      // Полная перезагрузка — чтобы middleware подхватил новый cookie администратора
      window.location.href = '/admin'
    } catch {
      setStopping(false)
    }
  }

  return (
    <div style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      zIndex: 9999,
      background: '#1a1a2e',
      borderTop: '2px solid #e63946',
      color: '#fff',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 16,
      padding: '10px 24px',
      fontFamily: 'sans-serif',
      fontSize: 13,
    }}>
      <span style={{ color: '#e63946', fontWeight: 600 }}>●</span>
      <span>
        Режим просмотра: вы видите сайт от лица{' '}
        <strong>{name}</strong>{' '}
        <span style={{ color: 'rgba(255,255,255,0.5)' }}>({status.target_user?.email})</span>
      </span>
      <button
        onClick={handleStop}
        disabled={stopping}
        style={{
          marginLeft: 8,
          padding: '5px 14px',
          background: '#e63946',
          color: '#fff',
          border: 'none',
          borderRadius: 4,
          cursor: stopping ? 'default' : 'pointer',
          fontFamily: 'sans-serif',
          fontSize: 12,
          fontWeight: 600,
          opacity: stopping ? 0.7 : 1,
        }}
      >
        {stopping ? 'Выходим…' : 'Выйти из режима просмотра'}
      </button>
    </div>
  )
}
