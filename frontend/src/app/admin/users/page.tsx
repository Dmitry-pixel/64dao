'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { adminApi, getMe } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

export default function AdminUsersPage() {
  const router = useRouter()
  const [users, setUsers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [impersonating, setImpersonating] = useState<string | null>(null)
  const [roleChanging, setRoleChanging] = useState<string | null>(null)

  useEffect(() => {
    const init = async () => {
      try {
        const me = await getMe()
        if (me.role !== 'admin') { router.push('/dashboard'); return }
        const data = await adminApi.users() as any[]
        setUsers(data)
      } catch {
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  const filtered = users.filter(u =>
    u.email.includes(search) ||
    (u.full_name ?? '').toLowerCase().includes(search.toLowerCase()) ||
    (u.company_name ?? '').toLowerCase().includes(search.toLowerCase())
  )

  async function handleImpersonate(userId: string, email: string) {
    if (!confirm(`Войти в систему от лица ${email}?`)) return
    setImpersonating(userId)
    try {
      await adminApi.impersonate(userId)
      router.push('/dashboard')
    } catch (e: any) {
      alert(e.message ?? 'Ошибка')
      setImpersonating(null)
    }
  }

  async function handleRoleToggle(u: any) {
    const newRole = u.role === 'admin' ? 'user' : 'admin'
    if (!confirm(`Изменить роль ${u.email} на «${newRole}»?`)) return
    setRoleChanging(u.id)
    try {
      await adminApi.setUserRole(u.id, newRole)
      setUsers(prev => prev.map(x => x.id === u.id ? { ...x, role: newRole } : x))
    } catch (e: any) {
      alert(e.message ?? 'Ошибка')
    } finally {
      setRoleChanging(null)
    }
  }

  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>Загрузка…</div>

  return (
    <>
      <AdminNav current="users" />
      <div className="admin-shell">
        <AdminSide current="users" stats={{ users: users.length, strategies: 0, reports: 0 }} />
        <div className="admin-main">
          <div className="admin-header">
            <div>
              <span className="label-red">Пользователи</span>
              <h1>Все пользователи</h1>
            </div>
            <div className="row" style={{ gap: 8 }}>
              <input
                placeholder="Поиск по email или компании…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{ padding: '8px 12px', border: '1px solid var(--line)', borderRadius: 5, fontFamily: 'sans-serif', fontSize: 13, minWidth: 280, background: 'var(--card)', outline: 'none' }}
              />
            </div>
          </div>

          <table className="tbl">
            <thead>
              <tr>
                <th>Email</th>
                <th>Имя</th>
                <th>Компания</th>
                <th>Роль</th>
                <th>Создан</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(u => (
                <tr key={u.id} style={{ cursor: u.role !== 'admin' ? 'pointer' : 'default' }}>
                  <td><strong>{u.email}</strong></td>
                  <td>{u.full_name ?? '—'}</td>
                  <td>{u.company_name ?? '—'}</td>
                  <td>
                    <button
                      onClick={() => handleRoleToggle(u)}
                      disabled={roleChanging === u.id}
                      style={{
                        background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                        opacity: roleChanging === u.id ? 0.5 : 1,
                      }}
                      title="Нажмите чтобы сменить роль"
                    >
                      {u.role === 'admin'
                        ? <span className="pill pill-pending">admin</span>
                        : <span className="pill pill-completed">user</span>
                      }
                    </button>
                  </td>
                  <td style={{ fontFamily: 'sans-serif', fontSize: 13 }}>
                    {new Date(u.created_at).toLocaleDateString('ru')}
                  </td>
                  <td>
                    {u.role !== 'admin' && (
                      <button
                        onClick={() => handleImpersonate(u.id, u.email)}
                        disabled={impersonating === u.id}
                        className="btn btn-ghost"
                        style={{ padding: '5px 12px', fontSize: 12 }}
                      >
                        {impersonating === u.id ? '…' : '👁 Войти как'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="row" style={{ justifyContent: 'space-between', marginTop: 18 }}>
            <span className="faint">Показано {filtered.length} из {users.length}</span>
          </div>
        </div>
      </div>
    </>
  )
}
