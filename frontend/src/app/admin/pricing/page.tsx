'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

export default function AdminPricingPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMe()
      .then(me => { if (me.role !== 'admin') router.push('/dashboard') })
      .catch(() => router.push('/login'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>Загрузка…</div>

  return (
    <div className="app-layout">
      <AdminNav current="pricing" />
      <div className="admin-body">
        <AdminSide current="pricing" />
        <main className="admin-main">
          <h1>Тариф & цена</h1>
          <p style={{ color: 'var(--text-mute)' }}>Раздел в разработке.</p>
        </main>
      </div>
    </div>
  )
}
