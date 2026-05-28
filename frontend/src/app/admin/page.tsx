'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getMe, adminApi, logout, reportDownloadUrl, type AuthUser } from '@/lib/api'

type Tab = 'stats' | 'users' | 'strategies' | 'reports'
type View = 'list' | 'editor'

const LIFECYCLE_STAGES = ['Зарождение', 'Расцвет', 'Зрелость', 'Обновление', 'Упадок']
const SCENARIO_ROWS = [
  'Инновационная стратегия', 'Инновационный тип', 'Ценностная дисциплина',
  'Принципы лидерства', 'Стратегия роста', 'Фокус'
]
const CATEGORIES = [
  'ПЛАНИРОВАНИЕ', 'РОСТ И ПРОИЗВОДИТЕЛЬНОСТЬ', 'ОБРАТНАЯ СВЯЗЬ', 'РЕКЛАМА',
  'РИСК', 'ВЫБОР ПРОДУКТА', 'СЕРВИС', 'СТАРТАП', 'ИНВЕСТИЦИИ И ФИНАНСЫ',
  'ДОГОВОРА И СОГЛАШЕНИЯ', 'СИНХРОНИЗАЦИЯ', 'ТВОРЧЕСКИЙ ВКЛАД',
  'ВЗАИМОДЕЙСТВИЕ', 'ДОСТАТОЧНОСТЬ РЕСУРСОВ', 'ИССЛЕДОВАНИЕ И РАЗРАБОТКА',
  'МЕЖДУНАРОДНАЯ ТОРГОВЛЯ', 'ИСТОЧНИКИ НЕУДАЧ', 'ИСТОЧНИКИ УДАЧИ'
]

const EMPTY_STRATEGY = {
  combination: '',
  title: null as string | null,
  stratagema_title: null as string | null,
  lifecycle_stage: null as string | null,
  lifecycle_description: null as string | null,
  scenario_text: null as string | null,
  marketing_text: null as string | null,
  management_text: null as string | null,
  transition_title: null as string | null,
  transition_lifecycle_stage: null as string | null,
  transition_description: null as string | null,
  scenario: null as Record<string, string> | null,
  current_state: null as Record<string, string> | null,
  is_published: false,
}

export default function AdminPage() {
  const router = useRouter()
  const [user, setUser] = useState<AuthUser | null>(null)
  const [tab, setTab] = useState<Tab>('stats')
  const [view, setView] = useState<View>('list')
  const [stats, setStats] = useState<any>(null)
  const [users, setUsers] = useState<any[]>([])
  const [strategies, setStrategies] = useState<any[]>([])
  const [reports, setReports] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [editingStrategy, setEditingStrategy] = useState<any>(null)
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const [isNew, setIsNew] = useState(false)
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [transitionImageFile, setTransitionImageFile] = useState<File | null>(null)

  useEffect(() => {
    getMe()
      .then(u => {
        if (u.role !== 'admin') { router.push('/dashboard'); return }
        setUser(u)
        return adminApi.stats().then((s: any) => setStats(s))
      })
      .catch(() => router.push('/login'))
      .finally(() => setLoading(false))
  }, [router])

  async function loadTab(t: Tab) {
    setTab(t)
    setView('list')
    if (t === 'users' && users.length === 0)
      adminApi.users().then((d: any) => setUsers(d))
    if (t === 'strategies' && strategies.length === 0)
      adminApi.strategies().then((d: any) => setStrategies(d))
    if (t === 'reports' && reports.length === 0)
      adminApi.reports().then((d: any) => setReports(d))
  }

  async function handleLogout() {
    await logout()
    router.push('/login')
  }

  function openEditor(strategy: any) {
    setEditingStrategy({ ...EMPTY_STRATEGY, ...strategy })
    setIsNew(false)
    setView('editor')
    setSaveMsg('')
    setImageFile(null)
    setTransitionImageFile(null)
  }

  function openNewEditor() {
    setEditingStrategy({ ...EMPTY_STRATEGY })
    setIsNew(true)
    setView('editor')
    setSaveMsg('')
    setImageFile(null)
    setTransitionImageFile(null)
  }

  function fieldChange(key: string, val: any) {
    setEditingStrategy((prev: any) => ({ ...prev, [key]: val }))
  }

  function scenarioChange(row: string, val: string) {
    setEditingStrategy((prev: any) => ({
      ...prev,
      scenario: { ...(prev.scenario || {}), [row]: val }
    }))
  }

  function currentStateChange(cat: string, val: string) {
    setEditingStrategy((prev: any) => ({
      ...prev,
      current_state: { ...(prev.current_state || {}), [cat]: val }
    }))
  }

  async function saveStrategy() {
    if (!editingStrategy) return
    setSaving(true)
    setSaveMsg('')
    try {
      let saved: any
      if (isNew) {
        saved = await adminApi.createStrategy(editingStrategy)
        setStrategies(prev => [saved, ...prev])
      } else {
        saved = await adminApi.updateStrategy(editingStrategy.id, editingStrategy)
        setStrategies(prev => prev.map((s: any) => s.id === saved.id ? saved : s))
      }

      if (imageFile && saved.id) {
        await adminApi.uploadImage(saved.id, imageFile)
      }
      if (transitionImageFile && saved.id) {
        await adminApi.uploadImage(saved.id, transitionImageFile)
        setTransitionImageFile(null)
      }

      setEditingStrategy(saved)
      setIsNew(false)
      setSaveMsg('Сохранено ✓')
      if (stats) adminApi.stats().then((s: any) => setStats(s))
    } catch (e: any) {
      setSaveMsg('Ошибка: ' + (e.message || 'неизвестная'))
    } finally {
      setSaving(false)
    }
  }

  async function togglePublish(id: string, current: boolean) {
    await adminApi.updateStrategy(id, { is_published: !current })
    setStrategies(prev => prev.map((s: any) => s.id === id ? { ...s, is_published: !current } : s))
  }


  async function changeRole(id: string, role: string) {
    await adminApi.setUserRole(id, role as 'user' | 'admin')
    setUsers((prev: any[]) => prev.map((u: any) => u.id === id ? { ...u, role } : u))
  }

  async function deleteUserConfirm(id: string, email: string) {
    if (!confirm(`Вы действительно хотите удалить пользователя ${email}?`)) return
    await adminApi.deleteUser(id)
    setUsers((prev: any[]) => prev.filter((u: any) => u.id !== id))
  }

  if (loading) return (
    <div style={S.center}><p style={{ color: '#666', fontFamily: 'sans-serif' }}>Загрузка...</p></div>
  )

  // ── Редактор стратегии ────────────────────────────────────────────────────
  if (tab === 'strategies' && view === 'editor' && editingStrategy) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg,#e8e4db)', fontFamily: 'Georgia,serif' }}>
        {/* Топбар */}
        <div style={S.navbar}>
          <span style={S.navBrand}>64 ДАО · Админ</span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button style={{...S.btnGhost, color:'#e8e4db', borderColor:'rgba(232,228,219,0.3)'}} onClick={() => { setView('list'); setTab('stats') }}>← Админка</button>
            <button style={{...S.btnGhost, color:'#e8e4db', borderColor:'rgba(232,228,219,0.3)'}} onClick={() => setView('list')}>← К стратегиям</button>
            <button style={S.btnPrimary} onClick={saveStrategy} disabled={saving}>
              {saving ? 'Сохранение...' : 'Сохранить и опубликовать'}
            </button>
            {saveMsg && <span style={{ alignSelf: 'center', fontSize: 13, color: saveMsg.startsWith('Ош') ? '#c0392b' : '#2d6a2d', fontFamily: 'sans-serif' }}>{saveMsg}</span>}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 24, maxWidth: 1200, margin: '0 auto', padding: '32px 24px' }}>
          {/* Левая колонка — поля */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

            {/* Заголовок */}
            <div style={S.editorSection}>
              <span style={S.labelRed}>Заголовок</span>
              <h3 style={S.sectionH3}>Основные поля</h3>
              <p style={S.editorHelp}>Это видно пользователю в отчёте — будьте точны.</p>
              {isNew && (
                <div style={S.field}>
                  <label style={S.label}>Комбинация (6 символов A/B)</label>
                  <input style={S.input} placeholder="Например: ABABAB"
                    value={editingStrategy.combination || ''}
                    onChange={e => fieldChange('combination', e.target.value.toUpperCase())} />
                </div>
              )}
              {!isNew && (
                <div style={{ ...S.field, marginBottom: 8 }}>
                  <span style={{ fontFamily: 'monospace', fontSize: 18, letterSpacing: 3, color: '#1a2540', fontWeight: 700 }}>{editingStrategy.combination}</span>
                </div>
              )}
              <div style={S.field}>
                <label style={S.label}>Заголовок</label>
                <input style={S.input} placeholder="Название стратегии"
                  value={editingStrategy.title || ''}
                  onChange={e => fieldChange('title', e.target.value)} />
              </div>
              <div style={S.field}>
                <label style={S.label}>Стратагема (одной строкой)</label>
                <input style={S.input} placeholder="Краткое название стратагемы"
                  value={editingStrategy.stratagema_title || ''}
                  onChange={e => fieldChange('stratagema_title', e.target.value)} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div style={S.field}>
                  <label style={S.label}>Стадия жизненного цикла</label>
                  <select style={S.select}
                    value={editingStrategy.lifecycle_stage || ''}
                    onChange={e => fieldChange('lifecycle_stage', e.target.value)}>
                    <option value="">— выберите —</option>
                    {LIFECYCLE_STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div style={S.field}>
                  <label style={S.label}>Описание стадии</label>
                  <input style={S.input} placeholder="Краткое описание"
                    value={editingStrategy.lifecycle_description || ''}
                    onChange={e => fieldChange('lifecycle_description', e.target.value)} />
                </div>
              </div>
              <div style={{ ...S.field, marginBottom: 0 }}>
                <label style={S.label}>Сценарий (краткое описание)</label>
                <textarea style={S.textarea} rows={3}
                  placeholder="Внешняя структура остаётся прежней, но внутри происходят глубокие изменения..."
                  value={editingStrategy.scenario_text || ''}
                  onChange={e => fieldChange('scenario_text', e.target.value)} />
              </div>
            </div>

            {/* Маркетинг */}
            <div style={S.editorSection}>
              <span style={S.labelRed}>Маркетинг</span>
              <h3 style={S.sectionH3}>Рекомендации по маркетингу</h3>
              <p style={S.editorHelp}>Что компании делать с продуктом, ценой, каналами и коммуникацией на этом сценарии.</p>
              <div style={{ ...S.field, marginBottom: 0 }}>
                <textarea style={S.textarea} rows={6}
                  placeholder="Не запускайте новые продукты — углубите ценность существующих..."
                  value={editingStrategy.marketing_text || ''}
                  onChange={e => fieldChange('marketing_text', e.target.value)} />
              </div>
            </div>

            {/* Управление */}
            <div style={S.editorSection}>
              <span style={S.labelRed}>Управление</span>
              <h3 style={S.sectionH3}>Рекомендации по управлению</h3>
              <p style={S.editorHelp}>Как руководителю организовать команду и принятие решений.</p>
              <div style={{ ...S.field, marginBottom: 0 }}>
                <textarea style={S.textarea} rows={6}
                  placeholder="Проведите ревизию процессов. Назначьте владельцев ключевых этапов..."
                  value={editingStrategy.management_text || ''}
                  onChange={e => fieldChange('management_text', e.target.value)} />
              </div>
            </div>

            {/* Переходное состояние */}
            <div style={S.editorSection}>
              <span style={S.labelRed}>Переходное состояние</span>
              <h3 style={S.sectionH3}>Целевая комбинация</h3>
              <p style={S.editorHelp}>Куда система рекомендует двигаться через 12–18 месяцев.</p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div style={S.field}>
                  <label style={S.label}>Целевая комбинация</label>
                  <input style={S.input} placeholder="BABABA"
                    value={editingStrategy.transition_description || ''}
                    onChange={e => fieldChange('transition_description', e.target.value)} />
                </div>
                <div style={S.field}>
                  <label style={S.label}>Название перехода</label>
                  <input style={S.input} placeholder="Постепенное движение"
                    value={editingStrategy.transition_title || ''}
                    onChange={e => fieldChange('transition_title', e.target.value)} />
                </div>
              </div>
              <div style={{ ...S.field, marginBottom: 0 }}>
                <label style={S.label}>Стадия перехода</label>
                <select style={S.select}
                  value={editingStrategy.transition_lifecycle_stage || ''}
                  onChange={e => fieldChange('transition_lifecycle_stage', e.target.value)}>
                  <option value="">— выберите —</option>
                  {LIFECYCLE_STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div style={{ ...S.field, marginTop: 14, marginBottom: 0 }}>
                <label style={S.label}>Изображение для целевой комбинации</label>
                <div style={{ border: '2px dashed rgba(26,37,64,0.15)', borderRadius: 6, padding: 16, textAlign: 'center' as const, cursor: 'pointer', fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.4)' }}
                  onClick={() => document.getElementById('img-upload-transition')?.click()}>
                  {transitionImageFile ? `✓ ${transitionImageFile.name}` : (editingStrategy.image_url ? `✓ Загружено: ${editingStrategy.image_url.split('/').pop()}` : '+ загрузить изображение (JPG, PNG, WebP, макс. 5 МБ)')}
                  <input id="img-upload-transition" type="file" accept="image/jpeg,image/png,image/webp" style={{ display: 'none' }}
                    onChange={e => setTransitionImageFile(e.target.files?.[0] || null)} />
                </div>
                {editingStrategy.image_url && (
                  <img src={editingStrategy.image_url} alt="preview" style={{ marginTop: 8, maxWidth: '100%', maxHeight: 120, borderRadius: 4, objectFit: 'cover' as const }} />
                )}
              </div>
            </div>

            {/* Таблица сценария */}
            <div style={S.editorSection}>
              <span style={S.labelRed}>Сценарий стратагемы</span>
              <h3 style={S.sectionH3}>Таблица описания / действия</h3>
              <p style={S.editorHelp}>Левая колонка одинакова для всех гексаграмм. Правая — конкретные действия для этой комбинации.</p>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'sans-serif', fontSize: 13 }}>
                <thead>
                  <tr>
                    <th style={{ ...S.th, width: '45%' }}>Описание (одинаково)</th>
                    <th style={S.th}>Действие (для {editingStrategy.combination || 'этой комбинации'})</th>
                  </tr>
                </thead>
                <tbody>
                  {SCENARIO_ROWS.map(row => (
                    <tr key={row}>
                      <td style={S.td}>{row}</td>
                      <td style={S.td}>
                        <input
                          style={{ width: '100%', padding: '6px 10px', background: 'rgba(255,255,255,0.8)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 4, fontFamily: 'sans-serif', fontSize: 13, outline: 'none' }}
                          placeholder="Введите действие..."
                          value={(editingStrategy.scenario || {})[row] || ''}
                          onChange={e => scenarioChange(row, e.target.value)} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* 18 категорий */}
            <div style={S.editorSection}>
              <span style={S.labelRed}>Предположения и связи с будущим</span>
              <h3 style={S.sectionH3}>18 категорий</h3>
              <p style={S.editorHelp}>Заполните текстовые блоки по категориям для Маркетинга, Управления и Переходного состояния этой стратегии.</p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 16 }}>
                {CATEGORIES.map(cat => (
                  <div key={cat} style={S.catBlock}>
                    <label style={S.catLabel}>{cat}</label>
                    <textarea
                      style={{ width: '100%', padding: '9px 12px', background: 'rgba(255,255,255,0.6)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 4, fontFamily: 'sans-serif', fontSize: 12, resize: 'vertical', outline: 'none', lineHeight: 1.5, color: '#1a2540', minHeight: 60 }}
                      placeholder={`Описание для категории «${cat}»...`}
                      rows={3}
                      value={(editingStrategy.current_state || {})[cat] || ''}
                      onChange={e => currentStateChange(cat, e.target.value)} />
                  </div>
                ))}
              </div>
            </div>

          </div>

          {/* Правая колонка — превью и публикация */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Превью */}
            <div style={{ background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: 20 }}>
              <span style={{ ...S.labelRed, display: 'block', marginBottom: 8 }}>Превью</span>
              <div style={{ fontFamily: 'monospace', fontSize: 20, letterSpacing: 3, color: '#1a2540', fontWeight: 700, marginBottom: 8 }}>
                {editingStrategy.combination || '??????'}
              </div>
              <h3 style={{ fontFamily: 'Georgia,serif', fontSize: 18, fontWeight: 400, color: '#1a2540', margin: '0 0 4px' }}>
                {editingStrategy.title || 'Название не задано'}
              </h3>
              <span style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.5)' }}>
                {editingStrategy.combination} · {editingStrategy.lifecycle_stage || 'стадия не задана'}
              </span>

              {/* Загрузка изображения */}
              <div style={{ marginTop: 16, border: '2px dashed rgba(26,37,64,0.15)', borderRadius: 6, padding: 16, textAlign: 'center', cursor: 'pointer', fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.4)' }}
                onClick={() => document.getElementById('img-upload')?.click()}>
                {imageFile ? `✓ ${imageFile.name}` : (editingStrategy.image_url ? '✓ Изображение загружено' : '+ загрузить изображение')}
                <input id="img-upload" type="file" accept="image/jpeg,image/png,image/webp" style={{ display: 'none' }}
                  onChange={e => setImageFile(e.target.files?.[0] || null)} />
              </div>
            </div>

            {/* Публикация */}
            <div style={{ background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.1)', borderRadius: 8, padding: 20 }}>
              <span style={{ ...S.labelRed, display: 'block', marginBottom: 12 }}>Публикация</span>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <span style={{ fontFamily: 'sans-serif', fontSize: 13 }}>
                  {editingStrategy.is_published ? 'Опубликовано' : 'Черновик'}
                </span>
                <button
                  style={{ ...S.btnGhost, fontSize: 12 }}
                  onClick={() => fieldChange('is_published', !editingStrategy.is_published)}>
                  {editingStrategy.is_published ? 'Снять с публикации' : 'Опубликовать'}
                </button>
              </div>
              <button style={{ ...S.btnPrimary, width: '100%' }} onClick={saveStrategy} disabled={saving}>
                {saving ? 'Сохранение...' : 'Сохранить'}
              </button>
              {saveMsg && (
                <p style={{ fontFamily: 'sans-serif', fontSize: 12, marginTop: 8, color: saveMsg.startsWith('Ош') ? '#c0392b' : '#2d6a2d', textAlign: 'center' }}>
                  {saveMsg}
                </p>
              )}
            </div>

          </div>
        </div>
      </div>
    )
  }

  // ── Основная панель ───────────────────────────────────────────────────────
  return (
    <div style={S.page}>
      <div style={S.container}>

        <div style={S.header}>
          <h1 style={S.h1}>Панель администратора</h1>
          <button onClick={handleLogout} style={S.logoutBtn}>Выйти</button>
        </div>

        <div style={S.tabs}>
          {(['stats', 'users', 'strategies', 'reports'] as Tab[]).map(t => (
            <button key={t} onClick={() => loadTab(t)}
              style={{ ...S.tab, ...(tab === t ? S.tabActive : {}) }}>
              {tabLabel(t)}
            </button>
          ))}
        </div>

        {/* Статистика */}
        {tab === 'stats' && stats && (
          <div style={S.grid}>
            {[
              ['Пользователей', stats.total_users],
              ['Диагностик', stats.total_assessments],
              ['Отчётов', stats.total_reports],
              ['Стратегий', `${stats.published_strategies}/64`],
            ].map(([label, value]) => (
              <div key={label as string} style={S.statCard}>
                <div style={S.statValue}>{value}</div>
                <div style={S.statLabel}>{label}</div>
              </div>
            ))}
          </div>
        )}

        {/* Пользователи */}
        {tab === 'users' && (
          <div style={S.tableWrap}>
            <table style={S.table}>
              <thead>
                <tr>{['№', 'Email', 'Имя', 'Компания', 'Роль', 'Дата', ''].map(h => <th key={h} style={S.th2}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {users.map((u: any, idx: number) => (
                  <tr key={u.id} style={{ cursor: 'pointer' }} onClick={() => router.push(`/admin/user/${u.id}`)}>
                    <td style={{...S.td2, color: '#999', fontSize: 12, width: 40}}>{idx + 1}</td>
                    <td style={S.td2}>{u.email}</td>
                    <td style={S.td2}>{u.full_name || '—'}</td>
                    <td style={S.td2}>{u.company_name || '—'}</td>
                    <td style={S.td2}>
                      <select
                        value={u.role}
                        onClick={e => e.stopPropagation()}
                        onChange={e => changeRole(u.id, e.target.value)}
                        style={{ fontFamily: 'sans-serif', fontSize: 12, padding: '3px 6px', borderRadius: 6, border: '1px solid #e2e8f0', background: u.role === 'admin' ? '#fef3c7' : u.role === 'editor' ? '#ede9fe' : '#f1f5f9', color: u.role === 'admin' ? '#92400e' : u.role === 'editor' ? '#5b21b6' : '#475569', cursor: 'pointer' }}
                      >
                        <option value="user">user</option>
                        <option value="editor">editor</option>
                        <option value="admin">admin</option>
                      </select>
                    </td>
                    <td style={S.td2}>{new Date(u.created_at).toLocaleDateString('ru-RU')}</td>
                    <td style={S.td2}>
                      <button
                        onClick={e => { e.stopPropagation(); deleteUserConfirm(u.id, u.email) }}
                        style={{ background: 'none', border: '1px solid #fecaca', borderRadius: 6, padding: '3px 10px', fontSize: 12, cursor: 'pointer', color: '#dc2626', fontFamily: 'sans-serif' }}
                      >
                        Удалить
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Стратегии */}
        {tab === 'strategies' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <p style={{ color: '#666', fontSize: 13, fontFamily: 'sans-serif' }}>
                Опубликовано: {strategies.filter((s: any) => s.is_published).length} / {strategies.length}
              </p>
              <button style={S.btnPrimary} onClick={openNewEditor}>+ Создать стратегию</button>
            </div>
            <div style={S.tableWrap}>
              <table style={S.table}>
                <thead>
                  <tr>{['Комбинация', 'Название', 'Стадия', 'Статус', 'Обновлено', ''].map(h => <th key={h} style={S.th2}>{h}</th>)}</tr>
                </thead>
                <tbody>
                  {strategies.map((s: any) => (
                    <tr key={s.id} style={{ cursor: 'pointer' }} onClick={() => openEditor(s)}>
                      <td style={{ ...S.td2, fontFamily: 'monospace', letterSpacing: 2, fontWeight: 700 }}>{s.combination}</td>
                      <td style={S.td2}>{s.title || <span style={{ color: '#ccc' }}>—</span>}</td>
                      <td style={S.td2}>{s.lifecycle_stage || '—'}</td>
                      <td style={S.td2}>
                        <span style={s.is_published ? S.badgeOk : S.badgeDraft}>
                          {s.is_published ? 'Опубл.' : 'Черновик'}
                        </span>
                      </td>
                      <td style={S.td2}>{new Date(s.updated_at).toLocaleDateString('ru-RU')}</td>
                      <td style={S.td2} onClick={e => { e.stopPropagation(); togglePublish(s.id, s.is_published) }}>
                        <button style={S.actionBtn}>{s.is_published ? 'Скрыть' : 'Опубликовать'}</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Отчёты */}
        {tab === 'reports' && (
          <div style={S.tableWrap}>
            <table style={S.table}>
              <thead>
                <tr>{['Комбинация', 'Статус', 'Отчётов', 'Дата', ''].map(h => <th key={h} style={S.th2}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {reports.map((a: any) => (
                  <tr key={a.id}>
                    <td style={{ ...S.td2, fontFamily: 'monospace', letterSpacing: 2 }}>{a.method1_combination || '—'}</td>
                    <td style={S.td2}>{a.status}</td>
                    <td style={S.td2}>{a.reports.length}</td>
                    <td style={S.td2}>{new Date(a.created_at).toLocaleDateString('ru-RU')}</td>
                    <td style={S.td2}>
                      {a.reports[0] && (
                        <a href={reportDownloadUrl(a.reports[0].id)} target="_blank" rel="noreferrer" style={S.downloadLink}>↓ PDF</a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function tabLabel(t: Tab) {
  return { stats: 'Статистика', users: 'Пользователи', strategies: 'Стратегии', reports: 'Отчёты' }[t]
}

// ── Styles ────────────────────────────────────────────────────────────────────
const S: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#e8e4db', fontFamily: 'Arial,sans-serif', padding: '32px 16px' },
  center: { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#e8e4db' },
  container: { maxWidth: 960, margin: '0 auto' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  h1: { color: '#1a2540', margin: 0, fontSize: 24, fontWeight: 700, fontFamily: 'Georgia,serif' },
  logoutBtn: { background: 'none', border: 'none', color: '#c0392b', fontSize: 13, cursor: 'pointer', fontFamily: 'sans-serif' },
  tabs: { display: 'flex', gap: 4, marginBottom: 20, background: '#fff', padding: 4, borderRadius: 10 },
  tab: { flex: 1, padding: '8px 0', border: 'none', background: 'none', cursor: 'pointer', fontSize: 13, borderRadius: 7, color: '#666', fontFamily: 'sans-serif' },
  tabActive: { background: '#1a2540', color: '#fff', fontWeight: 600 },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12 },
  statCard: { background: '#fff', borderRadius: 10, padding: 20, textAlign: 'center' },
  statValue: { fontSize: 28, fontWeight: 700, color: '#1a2540', fontFamily: 'Georgia,serif' },
  statLabel: { fontSize: 12, color: '#999', marginTop: 4, fontFamily: 'sans-serif' },
  tableWrap: { background: '#fff', borderRadius: 10, overflow: 'auto' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13, fontFamily: 'sans-serif' },
  th2: { padding: '10px 14px', textAlign: 'left', color: '#999', fontWeight: 500, borderBottom: '1px solid #f0ede8' },
  td2: { padding: '10px 14px', borderBottom: '1px solid #f7f5f2', color: '#333' },
  badgeAdmin: { background: '#fef3c7', color: '#92400e', padding: '2px 8px', borderRadius: 20, fontSize: 11, fontWeight: 500 },
  badgeUser: { background: '#f1f5f9', color: '#475569', padding: '2px 8px', borderRadius: 20, fontSize: 11, fontWeight: 500 },
  badgeOk: { background: '#dcfce7', color: '#166534', padding: '2px 8px', borderRadius: 20, fontSize: 11, fontWeight: 500 },
  badgeDraft: { background: '#f1f5f9', color: '#475569', padding: '2px 8px', borderRadius: 20, fontSize: 11, fontWeight: 500 },
  actionBtn: { background: 'none', border: '1px solid #e2e8f0', borderRadius: 6, padding: '3px 10px', fontSize: 12, cursor: 'pointer', color: '#475569', fontFamily: 'sans-serif' },
  downloadLink: { color: '#1a2540', fontWeight: 600, textDecoration: 'none', fontSize: 13 },
  // Editor styles
  navbar: { background: '#1a2540', color: '#fff', padding: '14px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', position: 'sticky', top: 0, zIndex: 100 },
  navBrand: { fontFamily: 'Georgia,serif', fontSize: 16, color: '#e8e4db' },
  btnPrimary: { background: '#1a2540', color: '#fff', border: 'none', borderRadius: 6, padding: '9px 18px', fontSize: 13, cursor: 'pointer', fontFamily: 'sans-serif', fontWeight: 500 },
  btnGhost: { background: 'none', color: '#1a2540', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6, padding: '9px 18px', fontSize: 13, cursor: 'pointer', fontFamily: 'sans-serif' },
  editorSection: { background: 'rgba(255,255,255,0.65)', border: '1px solid rgba(26,37,64,0.08)', borderRadius: 8, padding: 24 },
  labelRed: { fontFamily: 'sans-serif', fontSize: 9, letterSpacing: 2, textTransform: 'uppercase' as const, color: '#c0392b', display: 'block', marginBottom: 6, fontWeight: 600 },
  sectionH3: { fontFamily: 'Georgia,serif', fontSize: 17, fontWeight: 400, color: '#1a2540', margin: '0 0 4px' },
  editorHelp: { fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.5)', marginBottom: 16, lineHeight: 1.5 },
  field: { marginBottom: 14 },
  label: { display: 'block', fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.5)', marginBottom: 5, letterSpacing: 0.3 },
  input: { width: '100%', padding: '9px 12px', background: 'rgba(255,255,255,0.8)', border: '1px solid rgba(26,37,64,0.12)', borderRadius: 5, fontFamily: 'sans-serif', fontSize: 13, outline: 'none', color: '#1a2540', boxSizing: 'border-box' as const },
  select: { width: '100%', padding: '9px 12px', background: 'rgba(255,255,255,0.8)', border: '1px solid rgba(26,37,64,0.12)', borderRadius: 5, fontFamily: 'sans-serif', fontSize: 13, outline: 'none', color: '#1a2540' },
  textarea: { width: '100%', padding: '9px 12px', background: 'rgba(255,255,255,0.8)', border: '1px solid rgba(26,37,64,0.12)', borderRadius: 5, fontFamily: 'sans-serif', fontSize: 13, outline: 'none', color: '#1a2540', resize: 'vertical' as const, lineHeight: 1.6, boxSizing: 'border-box' as const },
  th: { padding: '9px 12px', textAlign: 'left' as const, fontFamily: 'sans-serif', fontSize: 11, color: 'rgba(26,37,64,0.5)', borderBottom: '1px solid rgba(26,37,64,0.08)', fontWeight: 500 },
  td: { padding: '8px 12px', fontFamily: 'sans-serif', fontSize: 13, color: '#1a2540', borderBottom: '1px solid rgba(26,37,64,0.06)', verticalAlign: 'middle' as const },
  catBlock: { background: 'rgba(255,255,255,0.5)', border: '1px solid rgba(26,37,64,0.08)', borderRadius: 6, padding: 14 },
  catLabel: { fontFamily: 'sans-serif', fontSize: 10, letterSpacing: 2, textTransform: 'uppercase' as const, color: 'rgba(26,37,64,0.4)', display: 'block', marginBottom: 8, fontWeight: 600 },
}
