'use client'
import { useEffect, useState } from 'react'

export default function DashboardPage() {
  const [user, setUser] = useState<any>(null)

  useEffect(() => {
    fetch('/api/auth/me', { credentials: 'include' })
      .then(r => r.json())
      .then(d => setUser(d))
      .catch(() => {})
  }, [])

  return (
    <div style={{ minHeight:'100vh', background:'#e8e4db', display:'flex', alignItems:'center', justifyContent:'center', fontFamily:'Arial,sans-serif' }}>
      <div style={{ background:'white', borderRadius:'10px', padding:'40px', textAlign:'center' }}>
        <h1 style={{ color:'#1a2540', marginBottom:'10px' }}>Личный кабинет</h1>
        {user && <p style={{ color:'#666' }}>Добро пожаловать, {user.email}</p>}
        <a href="/api/auth/logout" style={{ color:'#c0392b', fontSize:'13px' }}>Выйти</a>
      </div>
    </div>
  )
}
