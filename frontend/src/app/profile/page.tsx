'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe, logout, type AuthUser } from '@/lib/api'
import { AppNav } from '@/components/AppNav'

const API = process.env.NEXT_PUBLIC_API_URL || ''

export default function ProfilePage() {
  const router = useRouter()
  const [user, setUser] = useState<AuthUser | null>(null)
  const [tab, setTab] = useState<'account' | 'company' | 'security'>('account')
  const [loading, setLoading] = useState(true)
  const [fullName, setFullName] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    getMe()
      .then(u => {
        setUser(u)
        setFullName(u.full_name || '')
        setCompanyName(u.company_name || '')
      })
      .catch(() => router.push('/login'))
      .finally(() => setLoading(false))
  }, [router])

  async function saveProfile() {
    setSaving(true); setMsg('')
    try {
      const res = await fetch(`${API}/api/auth/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ full_name: fullName, company_name: companyName }),
      })
      if (!res.ok) throw new Error()
      const u = await res.json()
      setUser(u)
      setMsg('Сохранено ✓')
    } catch {
      setMsg('Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  async function changePassword() {
    if (!oldPassword || !newPassword) return
    setSaving(true); setMsg('')
    try {
      const res = await fetch(`${API}/api/auth/change-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
      })
      if (!res.ok) {
        const d = await res.json()
        throw new Error(d.detail || 'Ошибка')
      }
      setMsg('Пароль изменён ✓')
      setOldPassword(''); setNewPassword('')
    } catch (e: any) {
      setMsg(e.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleLogout() {
    await logout()
    router.push('/login')
  }

  if (loading) return (
    <div style={{ minHeight: '100vh', background: '#e8e4db', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ fontFamily: 'sans-serif', color: 'rgba(26,37,64,0.4)' }}>Загрузка...</p>
    </div>
  )

  return (
    <div style={{ minHeight: '100vh', background: '#e8e4db' }}>
      <AppNav />

      {/* Hero */}
      <div style={S.hero}>
        <span style={S.labelRed}>Настройки</span>
        <h1 style={S.heroH1}>Профиль и аккаунт</h1>
      </div>

      {/* Сетка */}
      <div style={S.settingsGrid}>
        {/* Сайдбар */}
        <aside style={S.settingsSide}>
          <button style={{ ...S.sideBtn, ...(tab === 'account' ? S.sideBtnOn : {}) }} onClick={() => { setTab('account'); setMsg('') }}>Аккаунт</button>
          <button style={{ ...S.sideBtn, ...(tab === 'company' ? S.sideBtnOn : {}) }} onClick={() => { setTab('company'); setMsg('') }}>Компания</button>
          <button style={{ ...S.sideBtn, ...(tab === 'security' ? S.sideBtnOn : {}) }} onClick={() => { setTab('security'); setMsg('') }}>Безопасность</button>
          <button style={{ ...S.sideBtn, color: '#c0392b', marginTop: 18 }} onClick={handleLogout}>Выйти из аккаунта</button>
        </aside>

        {/* Контент */}
        <div>
          {tab === 'account' && (
            <div style={S.card}>
              <span style={S.labelRed}>Личные данные</span>
              <h3 style={S.cardH3}>Аккаунт</h3>
              <div style={S.field}>
                <label style={S.label}>Имя и фамилия</label>
                <input style={S.input} value={fullName} onChange={e => setFullName(e.target.value)} placeholder="Введите имя" />
              </div>
              <div style={S.field}>
                <label style={S.label}>Email</label>
                <input style={{ ...S.input, background: 'rgba(26,37,64,0.04)', color: 'rgba(26,37,64,0.5)' }} value={user?.email || ''} readOnly />
                <p style={S.fieldHint}>При смене email потребуется подтверждение через OTP-код.</p>
              </div>
              {msg && <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: msg.includes('✓') ? '#166534' : '#c0392b', marginBottom: 12 }}>{msg}</p>}
              <div style={S.rowEnd}>
                <button style={S.btnGhost} onClick={() => { setFullName(user?.full_name || ''); setMsg('') }}>Отменить</button>
                <button style={S.btnPrimary} onClick={saveProfile} disabled={saving}>{saving ? 'Сохранение...' : 'Сохранить'}</button>
              </div>
            </div>
          )}

          {tab === 'company' && (
            <div style={S.card}>
              <span style={S.labelRed}>Организация</span>
              <h3 style={S.cardH3}>Компания</h3>
              <div style={S.field}>
                <label style={S.label}>Название компании</label>
                <input style={S.input} value={companyName} onChange={e => setCompanyName(e.target.value)} placeholder="ООО «Название»" />
              </div>
              {msg && <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: msg.includes('✓') ? '#166534' : '#c0392b', marginBottom: 12 }}>{msg}</p>}
              <div style={S.rowEnd}>
                <button style={S.btnGhost} onClick={() => { setCompanyName(user?.company_name || ''); setMsg('') }}>Отменить</button>
                <button style={S.btnPrimary} onClick={saveProfile} disabled={saving}>{saving ? 'Сохранение...' : 'Сохранить'}</button>
              </div>
            </div>
          )}

          {tab === 'security' && (
            <div style={S.card}>
              <span style={S.labelRed}>Пароль</span>
              <h3 style={S.cardH3}>Безопасность</h3>
              <div style={S.field}>
                <label style={S.label}>Текущий пароль</label>
                <input style={S.input} type="password" value={oldPassword} onChange={e => setOldPassword(e.target.value)} placeholder="Введите текущий пароль" />
              </div>
              <div style={S.field}>
                <label style={S.label}>Новый пароль</label>
                <input style={S.input} type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} placeholder="Не менее 8 символов" />
                <p style={S.fieldHint}>Минимум 8 символов. Используется как альтернатива OTP при входе.</p>
              </div>
              {msg && <p style={{ fontFamily: 'sans-serif', fontSize: 13, color: msg.includes('✓') ? '#166534' : '#c0392b', marginBottom: 12 }}>{msg}</p>}
              <div style={S.rowEnd}>
                <button style={S.btnGhost} onClick={() => { setOldPassword(''); setNewPassword(''); setMsg('') }}>Отменить</button>
                <button style={S.btnPrimary} onClick={changePassword} disabled={saving || !oldPassword || !newPassword}>{saving ? 'Сохранение...' : 'Сменить пароль'}</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

const S: Record<string, React.CSSProperties> = {
  nav: { background: '#cde3e3', borderBottom: '1px solid rgba(26,37,64,0.08)' },
  navInner: { maxWidth: 1200, margin: '0 auto', padding: '0 60px', height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24 },
  navLogo: { display: 'flex', alignItems: 'baseline', cursor: 'pointer', flexShrink: 0 },
  logo64: { fontFamily: 'Georgia,serif', fontSize: 20, color: '#c0392b' },
  logoDao: { fontFamily: 'Georgia,serif', fontSize: 20, color: '#1a2540' },
  navLinks: { display: 'flex', gap: 4 },
  navLink: { background: 'none', border: 'none', fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.6)', cursor: 'pointer', padding: '6px 12px', borderRadius: 5 },
  navLinkOn: { background: 'rgba(26,37,64,0.08)', color: '#1a2540' },
  navUser: { display: 'flex', alignItems: 'center', gap: 10 },
  navEmail: { fontFamily: 'sans-serif', fontSize: 13, color: 'rgba(26,37,64,0.55)' },
  avatar: { width: 32, height: 32, borderRadius: '50%', background: '#1a2540', color: '#e8e4db', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Georgia,serif', fontSize: 14 },
  hero: { maxWidth: 1200, margin: '0 auto', padding: '48px 60px 24px' },
  heroH1: { fontFamily: 'Georgia,serif', fontSize: 32, fontWeight: 400, color: '#1a2540', margin: '8px 0 0' },
  labelRed: { fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 2, textTransform: 'uppercase' as const, color: '#c0392b', fontWeight: 600 },
  settingsGrid: { maxWidth: 1200, margin: '0 auto', padding: '0 60px 60px', display: 'grid', gridTemplateColumns: '200px 1fr', gap: 32 },
  settingsSide: { fontFamily: 'sans-serif', fontSize: 13 },
  sideBtn: { display: 'block', width: '100%', textAlign: 'left' as const, padding: '9px 12px', background: 'none', border: 'none', borderRadius: 5, color: 'rgba(26,37,64,0.6)', cursor: 'pointer', fontFamily: 'sans-serif', fontSize: 13, marginBottom: 2 },
  sideBtnOn: { background: 'rgba(26,37,64,0.06)', color: '#1a2540' },
  card: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: '24px 28px' },
  cardH3: { fontFamily: 'Georgia,serif', fontSize: 20, fontWeight: 400, color: '#1a2540', margin: '6px 0 20px' },
  field: { marginBottom: 18 },
  label: { display: 'block', fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.6)', marginBottom: 6 },
  input: { width: '100%', padding: '10px 14px', background: 'rgba(255,255,255,0.8)', border: '1px solid rgba(26,37,64,0.15)', borderRadius: 6, fontFamily: 'sans-serif', fontSize: 14, color: '#1a2540', outline: 'none', boxSizing: 'border-box' as const },
  fieldHint: { fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.4)', marginTop: 6, lineHeight: 1.5 },
  rowEnd: { display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 },
  btnPrimary: { background: '#1a2540', color: '#fff', border: 'none', borderRadius: 6, padding: '9px 20px', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer' },
  btnGhost: { background: 'none', color: '#1a2540', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6, padding: '9px 20px', fontFamily: 'sans-serif', fontSize: 13, cursor: 'pointer' },
}
