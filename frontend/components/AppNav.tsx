'use client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { logout, getMe } from '@/lib/api'
import { useEffect, useState } from 'react'

export function Logo() {
  return (
    <div className="logo-box">
      <div className="logo-sq"><span>64</span><span>DAO</span></div>
      <span className="logo-name">64 ДАО</span>
    </div>
  )
}

interface AppNavProps {
  current?: string
  role?: 'user' | 'admin'
}

export function AppNav({ current, role = 'user' }: AppNavProps) {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')

  useEffect(() => {
    getMe().then(me => {
      setEmail(me.email)
      setName(me.full_name ?? me.email.split('@')[0])
    }).catch(() => {})
  }, [])

  const handleLogout = async () => {
    try { await logout() } catch {}
    router.push('/login')
  }

  const initial = name ? name[0].toUpperCase() : '?'

  return (
    <nav className="appnav">
      <Logo />
      <div className="appnav-links">
        <Link href="/dashboard" className={current === 'dashboard' ? 'on' : ''}>Мои отчёты</Link>
        <Link href="/assessment/start" className="">Новая диагностика</Link>
        <Link href="/profile" className={current === 'profile' ? 'on' : ''}>Профиль</Link>
      </div>
      <div className="appnav-user">
        <span style={{ color: 'rgba(26,37,64,0.55)', fontFamily: 'sans-serif', fontSize: 13 }}>{email}</span>
        <div className="avatar">{initial}</div>
        <button onClick={handleLogout} style={{ background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)' }}>
          Выйти
        </button>
      </div>
    </nav>
  )
}