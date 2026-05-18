'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { adminApi, getMe } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

// A=0 (сплошная, Ян), B=1 (прерывистая, Инь) → 6-битный индекс → Unicode U+4DC0
function comboToHex(combo: string): string {
  if (!combo || combo.length !== 6) return '?'
  const offset = parseInt(combo.replace(/A/g, '0').replace(/B/g, '1'), 2)
  return String.fromCodePoint(0x4DC0 + offset)
}

// Правильный порядок гексаграмм 1–64 (combo → номер)
const HEXAGRAM_ORDER: Record<string, number> = {
  'AAAAAA':1,'BBBBBB':2,'ABBBAB':3,'BABBBA':4,'AAABAB':5,'BABAAA':6,'BABBBB':7,'BBBBAB':8,
  'AAABAA':9,'AABAAA':10,'AAABBB':11,'BBBAAA':12,'ABAAAA':13,'AAAABA':14,'BBABBB':15,'BBBABB':16,
  'ABBAAB':17,'BAABBA':18,'AABBBB':19,'BBBBAA':20,'ABBABA':21,'ABABBA':22,'BBBBBA':23,'ABBBBB':24,
  'ABBAAA':25,'AAABBA':26,'ABBBBA':27,'BAAAAB':28,'BABBAB':29,'ABAABA':30,'BBAAAB':31,'BAAABB':32,
  'BBAAAA':33,'AAAABB':34,'BBBABA':35,'ABABBB':36,'ABABAA':37,'AABABA':38,'BBABAB':39,'BABABB':40,
  'AABBBA':41,'ABBBAA':42,'AAAAAB':43,'BAAAAA':44,'BBBAAB':45,'BAABBB':46,'BABAAB':47,'BAABAB':48,
  'ABAAAB':49,'BAAABA':50,'ABBABB':51,'BBABBA':52,'BBABAA':53,'AABABB':54,'ABAABB':55,'BBAABA':56,
  'BABBAA':57,'AABAAB':58,'BAABAA':59,'AABBAB':60,'AABBAA':61,'BBAABB':62,'ABABAB':63,'BABABA':64,
}

export default function AdminStrategiesPage() {
  const router = useRouter()
  const [strategies, setStrategies] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    const init = async () => {
      try {
        const me = await getMe()
        if (me.role !== 'admin') { router.push('/dashboard'); return }
        const data = await adminApi.strategies() as any[]
        // Сортируем по правильному порядку гексаграмм 1–64
        data.sort((a: any, b: any) => (HEXAGRAM_ORDER[a.combination] ?? 99) - (HEXAGRAM_ORDER[b.combination] ?? 99))
        setStrategies(data)
      } catch {
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  const filtered = strategies.filter(s =>
    (s.combination ?? '').includes(search.toUpperCase()) ||
    (s.title ?? '').toLowerCase().includes(search.toLowerCase())
  )

  const published = strategies.filter(s => s.is_published).length

  if (loading) return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)' }}>Загрузка…</div>

  return (
    <>
      <AdminNav current="strategies" />
      <div className="admin-shell">
        <AdminSide current="strategies" stats={{ users: 0, strategies: published, reports: 0 }} />
        <div className="admin-main">
          <div className="admin-header">
            <div>
              <span className="label-red">Контент</span>
              <h1>64 стратегии</h1>
            </div>
            <div className="row" style={{ gap: 8 }}>
              <input
                placeholder="Поиск…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{ padding: '8px 12px', border: '1px solid var(--line)', borderRadius: 5, fontFamily: 'sans-serif', fontSize: 13, minWidth: 240, background: 'var(--card)', outline: 'none' }}
              />
            </div>
          </div>

          <div className="card-flat" style={{ marginBottom: 14, display: 'flex', gap: 24, fontFamily: 'sans-serif', fontSize: 13 }}>
            <span><strong>{published} опубликовано</strong> <span className="faint" style={{ marginLeft: 6 }}>· {strategies.length - published} в черновиках</span></span>
            <span style={{ color: 'var(--text-mute)' }}>Каждая запись — одна из 64 гексаграмм.</span>
          </div>

          <table className="tbl">
            <thead>
              <tr>
                <th style={{ width: 40 }}>№</th>
                <th style={{ width: 60 }}>Гекс.</th>
                <th style={{ width: 100 }}>Комбинация</th>
                <th>Заголовок</th>
                <th>Стадия</th>
                <th>Статус</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => {
                const num = HEXAGRAM_ORDER[s.combination] ?? '?'
                return (
                  <tr key={s.id} style={{ cursor: 'pointer' }} onClick={() => router.push(`/admin/strategies/${s.combination}`)}>
                    <td style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'var(--text-mute)', textAlign: 'center' }}>{num}</td>
                    <td>
                      <span className="hex he