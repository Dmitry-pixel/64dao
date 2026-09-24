'use client'
/**
 * Админка · Сертификаты.
 *
 * Отвечает на один вопрос: работает ли доверие к API банка прямо сейчас и
 * когда истекает то, что им управляет. Только чтение — загрузки сертификатов
 * здесь нет намеренно, обоснование в backend/app/routers/certs.py.
 *
 * Страница открывается без опроса банка (probe=0): живой опрос ждёт до 15
 * секунд при его недоступности. Рукопожатие — явное действие по кнопке.
 */
import { useEffect, useState, type CSSProperties } from 'react'
import { useRouter } from 'next/navigation'
import { getMe, adminApi } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const CARD: CSSProperties = {
  background: 'rgba(255,255,255,0.65)',
  border: '1px solid rgba(26,37,64,0.08)',
  borderRadius: 10,
  padding: 24,
  marginBottom: 16,
}

const TH: CSSProperties = {
  textAlign: 'left', padding: '6px 12px', color: 'rgba(26,37,64,0.4)',
  fontWeight: 500, borderBottom: '1px solid rgba(26,37,64,0.08)',
}

const TD: CSSProperties = {
  padding: '8px 12px', borderBottom: '1px solid rgba(26,37,64,0.05)',
  color: '#1a2540', verticalAlign: 'top',
}

function human(days: number | null | undefined): string {
  if (days === null || days === undefined) return '—'
  if (days < 0) return `истёк ${-days} дн. назад`
  return `${days} дн.`
}

function dateRu(iso?: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return isNaN(d.getTime()) ? '—' : d.toLocaleDateString('ru-RU')
}

export default function AdminCertsPage() {
  const router = useRouter()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [probing, setProbing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getMe()
      .then(u => {
        if (u.role !== 'admin') { router.push('/dashboard'); return }
        return adminApi.certs(false).then((d: any) => setData(d))
      })
      .catch(() => router.push('/login'))
      .finally(() => setLoading(false))
  }, [router])

  async function runProbe() {
    setProbing(true)
    setError(null)
    try {
      setData(await adminApi.certs(true))
    } catch {
      setError('Не удалось выполнить проверку. Попробуйте ещё раз.')
    } finally {
      setProbing(false)
    }
  }

  if (loading) return (
    <div style={{ minHeight: '100vh', background: '#e8e4db', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'sans-serif', color: '#999' }}>
      Загрузка...
    </div>
  )

  const p = data?.probe
  // Три состояния, не два: null — банк не ответил (сетевой сбой), а не отказ
  // доверия. Смешивать их значит объявлять аварию при каждом таймауте.
  const hs = p == null ? null : p.handshake_ok
  const hsText = hs === true ? 'Проходит' : hs === false ? 'НЕ ПРОХОДИТ' : hs === null && p ? 'Банк не ответил' : 'Не проверялось'
  const hsColor = hs === true ? '#1a2540' : hs === false ? '#c0392b' : 'rgba(26,37,64,0.5)'

  const certs = [data?.root, data?.sub].filter(Boolean)

  return (
    <>
      <AdminNav current="certs" />
      <div className="admin-shell">
        <AdminSide current="certs" />
        <div className="admin-main admin-main-pad" style={{ padding: '32px 40px' }}>

          <span className="label-red">Система</span>
          <h1 style={{ fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400, color: '#1a2540', margin: '6px 0 28px' }}>
            Сертификаты
          </h1>

          <div style={CARD}>
            <span className="label-red">Доверие к API банка</span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 16, flexWrap: 'wrap', marginTop: 12, marginBottom: 12 }}>
              <div style={{ fontFamily: 'Georgia,serif', fontSize: 24, color: hsColor }}>{hsText}</div>
              <div style={{ fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.45)' }}>
                {data?.host} · бандл {data?.bundle_exists ? 'на месте' : 'ОТСУТСТВУЕТ'}
              </div>
            </div>

            {p && (
              <table style={{ borderCollapse: 'collapse', fontFamily: 'sans-serif', fontSize: 13, marginBottom: 12 }}>
                <tbody>
                  <tr>
                    <td style={{ ...TD, color: 'rgba(26,37,64,0.45)' }}>Издатель сертификата банка</td>
                    <td style={TD}>{p.issuer || 'не определён'}</td>
                  </tr>
                  <tr>
                    <td style={{ ...TD, color: 'rgba(26,37,64,0.45)' }}>Сертификат банка истекает через</td>
                    <td style={TD}>{human(p.leaf_days)}</td>
                  </tr>
                  {p.handshake_error && (
                    <tr>
                      <td style={{ ...TD, color: 'rgba(26,37,64,0.45)' }}>Ошибка</td>
                      <td style={{ ...TD, color: '#c0392b' }}>{p.handshake_error}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}

            <button
              onClick={runProbe}
              disabled={probing}
              style={{
                padding: '9px 16px', borderRadius: 6, cursor: probing ? 'default' : 'pointer',
                fontFamily: 'sans-serif', fontSize: 13, background: '#1a2540',
                color: '#fff', border: 'none',
              }}
            >
              {probing ? 'Проверяем…' : 'Проверить соединение с банком'}
            </button>

            <div style={{ fontFamily: 'sans-serif', fontSize: 11, lineHeight: 1.5, color: 'rgba(26,37,64,0.45)', marginTop: 10 }}>
              Проверка открывает TLS-соединение тем же хранилищем доверия, которым пользуется
              приложение при оплате. Занимает до 15 секунд, если банк не отвечает.
            </div>

            {error && (
              <div style={{ background: '#fff5f5', border: '1px solid rgba(192,57,43,0.2)', borderRadius: 8, padding: '10px 12px', fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.7)', marginTop: 10 }}>
                {error}
              </div>
            )}
          </div>

          <div style={CARD}>
            <span className="label-red">Сертификаты в образе</span>
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 12, fontFamily: 'sans-serif', fontSize: 13 }}>
              <thead>
                <tr>{['Файл', 'Кем выпущен', 'Действует до', 'Осталось', 'Отпечаток SHA-256'].map(h => (
                  <th key={h} style={TH}>{h}</th>
                ))}</tr>
              </thead>
              <tbody>
                {certs.map((c: any) => (
                  <tr key={c.file}>
                    <td style={TD}>
                      {c.subject || c.file}
                      <div style={{ fontSize: 11, color: 'rgba(26,37,64,0.45)', marginTop: 2 }}>
                        {c.role === 'anchor' ? 'якорь доверия' : 'справочно, в проверке цепочки не участвует'}
                      </div>
                    </td>
                    <td style={TD}>{c.issuer || '—'}</td>
                    <td style={TD}>{dateRu(c.not_after)}</td>
                    <td style={{ ...TD, color: c.role === 'anchor' && c.days_left < (data?.warn_days ?? 60) ? '#c0392b' : '#1a2540' }}>
                      {human(c.days_left)}
                    </td>
                    <td style={{ ...TD, fontFamily: 'monospace', fontSize: 10, wordBreak: 'break-all', maxWidth: 260 }}>
                      {c.sha256}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ fontFamily: 'sans-serif', fontSize: 11, lineHeight: 1.5, color: 'rgba(26,37,64,0.45)', marginTop: 12 }}>
              Отпечатки сверяются с gosuslugi.ru/crt. Тревога по сроку приходит только для
              корня: цепочку банк присылает целиком, и проверка упирается в него.
            </div>
          </div>

          <div style={CARD}>
            <span className="label-red">Последняя плановая проверка</span>
            <table style={{ borderCollapse: 'collapse', marginTop: 12, fontFamily: 'sans-serif', fontSize: 13 }}>
              <tbody>
                <tr>
                  <td style={{ ...TD, color: 'rgba(26,37,64,0.45)' }}>Когда</td>
                  <td style={TD}>{dateRu(data?.last_check?.checked_at)}</td>
                </tr>
                <tr>
                  <td style={{ ...TD, color: 'rgba(26,37,64,0.45)' }}>Запомненный издатель</td>
                  <td style={TD}>{data?.last_check?.last_issuer || '—'}</td>
                </tr>
                <tr>
                  <td style={{ ...TD, color: 'rgba(26,37,64,0.45)' }}>Рукопожатие тогда</td>
                  <td style={TD}>
                    {data?.last_check?.handshake_ok === true ? 'прошло'
                      : data?.last_check?.handshake_ok === false ? 'не прошло' : '—'}
                  </td>
                </tr>
              </tbody>
            </table>
            <div style={{ fontFamily: 'sans-serif', fontSize: 11, lineHeight: 1.5, color: 'rgba(26,37,64,0.45)', marginTop: 12 }}>
              Задача запускается раз в неделю и шлёт письмо только при смене состояния:
              «сломалось» и потом «починилось». Отсутствие писем означает, что состояние
              не менялось, а не что проверок не было.
            </div>
          </div>

          <div style={CARD}>
            <span className="label-red">Если рукопожатие не проходит</span>
            <ol style={{ fontFamily: 'sans-serif', fontSize: 13, lineHeight: 1.7, color: 'rgba(26,37,64,0.7)', margin: '12px 0 0', paddingLeft: 20 }}>
              <li>Посмотреть, сменился ли издатель — строка выше. Смена означает переход
                банка на другой удостоверяющий центр.</li>
              <li>На сервере посмотреть живую цепочку:<br />
                <code style={{ fontSize: 11, wordBreak: 'break-all' }}>
                  echo | openssl s_client -connect {data?.host}:443 -servername {data?.host} -showcerts 2&gt;/dev/null | grep -E &apos;^ *[0-9]+ s:|^ *i:|NotAfter&apos;
                </code>
              </li>
              <li>Если корень новый — <code>./deploy/scripts/fetch-russian-ca.sh</code>,
                сверить отпечатки с gosuslugi.ru/crt, коммит,
                <code> docker compose build backend</code>, <code>up -d</code>.</li>
              <li>Приёмка: тестовый платёж 1 ₽ и возврат через раздел «Заказы и возвраты».</li>
            </ol>
            <div style={{ fontFamily: 'sans-serif', fontSize: 11, lineHeight: 1.5, color: 'rgba(26,37,64,0.45)', marginTop: 12 }}>
              Сертификаты лежат в образе, поэтому нужна пересборка, а не перезапуск.
              Подробности — DEPLOY.md, раздел 8a.
            </div>
          </div>

        </div>
      </div>
    </>
  )
}
