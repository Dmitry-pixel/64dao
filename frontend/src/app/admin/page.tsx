'use client'
import { useEffect, useState } from 'react'

export default function AdminPage() {
  const [stats, setStats] = useState<any>(null)

  useEffect(() => {
    fetch('/api/admin/stats', { credentials: 'include' })
      .then(r => r.json())
      .then(d => setStats(d))
      .catch(() => {})
  }, [])

  return (
    <div style={{ minHeight:'100vh', background:'#e8e4db', display:'flex', alignItems:'center', justifyContent:'center', fontFamily:'Arial,sans-serif' }}>
      <div style={{ background:'white', borderRadius:'10px', padding:'40px', textAlign:'center', minWidth:'300px' }}>
        <h1 style={{ color:'#1a2540', marginBottom:'20px' }}>Панель администратора</h1>
        {stats && (
          <div>
            <p>Пользователей: {stats.total_users}</p>
            <p>Диагностик: {stats.total_assessments}</p>
            <p>Стратегий: {stats.published_strategies}/64</p>
          </div>
        )}
        <a href="/api/auth/logout" style={{ color:'#c0392b', fontSize:'13px' }}>Выйти</a>
      </div>
    </div>
  )
}
