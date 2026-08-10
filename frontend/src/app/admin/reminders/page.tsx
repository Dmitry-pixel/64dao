'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { getMe, adminApi, type RemindersSettings } from '@/lib/api'
import { AdminNav, AdminSide } from '@/components/AdminNav'

const DAYS_MIN = 7
const DAYS_MAX = 3650

const card: React.CSSProperties = {
  border: '1px solid rgba(26,37,64,0.09)',
  borderRadius: 10,
  padding: '20px 24px',
  background: 'rgba(255,255,255,0.55)',
  marginBottom: 16,
}

const capStyle: React.CSSProperties = {
  fontFamily: 'sans-serif',
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: 1.5,
  textTransform: 'uppercase',
  color: 'rgba(26,37,64,0.4)',
  marginBottom: 12,
}

const hintStyle: React.CSSProperties = {
  fontFamily: 'sans-serif',
  fontSize: 12,
  color: 'var(--text-mute)',
  lineHeight: 1.6,
  margin: '6px 0 0 32px',
}

function Toggle({ checked, disabled, onChange, title }: {
  checked: boolean
  disabled?: boolean
  onChange: (v: boolean) => void
  title: string
}) {
  return (
    <label style={{
      display: 'flex', alignItems: 'center', gap: 12,
      cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.45 : 1,
    }}>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={e => onChange(e.target.checked)}
        style={{ width: 18, height: 18, cursor: disabled ? 'default' : 'pointer' }}
      />
      <span style={{ fontFamily: 'sans-serif', fontSize: 14, color: 'var(--text)' }}>
        {title}
      </span>
    </label>
  )
}

export default function AdminRemindersPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [cfg, setCfg] = useState<RemindersSettings | null>(null)
  const [daysInput, setDaysInput] = useState('90')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    getMe()
      .then(me => { if (me.role !== 'admin') router.push('/dashboard') })
      .catch(() => router.push('/login'))
    adminApi.remindersSettings()
      .then(data => { setCfg(data); setDaysInput(String(data.repeat_days)) })
      .catch(() => setError('Не удалось загрузить настройки рассылки'))
      .finally(() => setLoading(false))
  }, [])

  const patch = (p: Partial<RemindersSettings>) => {
    setSaved(false)
    setNotice('')
    setCfg(prev => (prev ? { ...prev, ...p } : prev))
  }

  const handleSave = async () => {
    if (!cfg) return
    setSaving(true)
    setError('')
    setNotice('')
    const asked = parseInt(daysInput, 10)
    const payload: RemindersSettings = {
      ...cfg,
      repeat_days: Number.isFinite(asked) ? asked : cfg.repeat_days,
    }
    try {
      const back = await adminApi.saveRemindersSettings(payload)
      // Сервер зажимает период в допустимые границы. Показываем результат,
      // а не то, что было введено: иначе поле врёт о сохранённом значении.
      if (back.repeat_days !== payload.repeat_days) {
        setNotice(`Период скорректирован до ${back.repeat_days} дн.: допустимо от ${DAYS_MIN} до ${DAYS_MAX}.`)
      }
      setCfg(back)
      setDaysInput(String(back.repeat_days))
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch {
      setError('Не удалось сохранить. Попробуйте ещё раз.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      minHeight: '100vh', fontFamily: 'sans-serif', color: 'var(--text-mute)',
    }}>
      Загрузка…
    </div>
  )

  return (
    <>
      <AdminNav current="reminders" />
      <div className="admin-shell">
        <AdminSide current="reminders" />
        <div className="admin-main admin-main-pad" style={{ padding: '32px 40px' }}>

          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
            marginBottom: 28, flexWrap: 'wrap', gap: 16,
          }}>
            <div>
              <span className="label-red">Система</span>
              <h1 style={{
                fontFamily: 'Georgia,serif', fontSize: 28, fontWeight: 400,
                color: 'var(--text)', margin: '6px 0 4px',
              }}>
                Рассылка
              </h1>
              <p style={{
                fontFamily: 'sans-serif', fontSize: 13,
                color: 'var(--text-mute)', margin: 0,
              }}>
                Что и как часто уходит пользователям. Тексты писем — в разделе{' '}
                <Link href="/admin/email-templates" style={{ color: 'var(--blue)' }}>
                  Email-шаблоны
                </Link>.
              </p>
            </div>
            <button
              className={`btn ${saved ? 'btn-ghost' : 'btn-primary'}`}
              style={{ padding: '9px 24px', fontSize: 13, opacity: saving ? 0.6 : 1 }}
              disabled={saving || !cfg}
              onClick={handleSave}
            >
              {saving ? 'Сохраняем…' : saved ? '✓ Сохранено' : 'Сохранить'}
            </button>
          </div>

          {error && (
            <div style={{
              border: '1px solid rgba(192,57,43,0.3)', borderRadius: 8,
              padding: '12px 16px', marginBottom: 16, background: 'rgba(192,57,43,0.06)',
              fontFamily: 'sans-serif', fontSize: 13, color: 'var(--red)',
            }}>
              {error}
            </div>
          )}

          {notice && (
            <div style={{
              border: '1px solid rgba(30,58,138,0.25)', borderRadius: 8,
              padding: '12px 16px', marginBottom: 16, background: 'rgba(30,58,138,0.05)',
              fontFamily: 'sans-serif', fontSize: 13, color: 'var(--blue)',
            }}>
              {notice}
            </div>
          )}

          {cfg && (
            <div style={{ maxWidth: 720 }}>

              <div style={card}>
                <div style={capStyle}>Общий выключатель</div>
                <Toggle
                  checked={cfg.enabled}
                  onChange={v => patch({ enabled: v })}
                  title={cfg.enabled ? 'Рассылка включена' : 'Рассылка выключена'}
                />
                <p style={hintStyle}>
                  Выключение останавливает все письма-напоминания. Транзакционные
                  письма (код входа, статус аккаунта) не затрагиваются:
                  они уходят в ответ на действие пользователя.
                </p>
              </div>

              <div style={{ ...card, opacity: cfg.enabled ? 1 : 0.55 }}>
                <div style={capStyle}>Пора повторить диагностику</div>
                <Toggle
                  checked={cfg.repeat_enabled}
                  disabled={!cfg.enabled}
                  onChange={v => patch({ repeat_enabled: v })}
                  title="Напоминать о повторной диагностике"
                />
                <p style={hintStyle}>
                  Одно письмо на компанию. Следующее уйдёт только после новой
                  диагностики: пока пользователь ничего не проходил, напоминание
                  не повторяется.
                </p>

                <div style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  marginTop: 20, marginLeft: 32, flexWrap: 'wrap',
                }}>
                  <span style={{ fontFamily: 'sans-serif', fontSize: 14, color: 'var(--text)' }}>
                    Отправлять через
                  </span>
                  <input
                    type="number"
                    min={DAYS_MIN}
                    max={DAYS_MAX}
                    value={daysInput}
                    disabled={!cfg.enabled || !cfg.repeat_enabled}
                    onChange={e => { setDaysInput(e.target.value); setSaved(false); setNotice('') }}
                    style={{
                      width: 90, padding: '8px 10px', fontFamily: 'sans-serif', fontSize: 14,
                      border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6,
                      background: 'rgba(255,255,255,0.8)', color: 'var(--text)',
                    }}
                  />
                  <span style={{ fontFamily: 'sans-serif', fontSize: 14, color: 'var(--text)' }}>
                    дн. после последней диагностики
                  </span>
                </div>
                <p style={{ ...hintStyle, marginTop: 8 }}>
                  Допустимо от {DAYS_MIN} до {DAYS_MAX}. Значение вне границ будет
                  подрезано при сохранении. Рекомендуемый ритм переоценки — 90 дней:
                  на меньшем интервале сдвиг по контурам обычно не виден.
                </p>
              </div>

              <div style={{ ...card, background: 'rgba(255,255,255,0.35)' }}>
                <div style={capStyle}>Как это работает</div>
                <ul style={{
                  fontFamily: 'sans-serif', fontSize: 13, color: 'var(--text-mute)',
                  lineHeight: 1.8, margin: 0, paddingLeft: 20,
                }}>
                  <li>Задание запускается раз в сутки в 06:00 по времени сервера.</li>
                  <li>Настройки применяются со следующего запуска, перезапуск не нужен.</li>
                  <li>Повторные письма не дублируются: отметка об отправке хранится у компании.</li>
                  <li>Журнал отправок: <code>/var/log/64dao-reminders.log</code>.</li>
                  <li>
                    Аварийный выключатель на уровне сервера — переменная
                    <code> REMINDERS_ENABLED</code> в <code>backend/.env</code>.
                    Она приоритетнее этой страницы.
                  </li>
                </ul>
              </div>

            </div>
          )}
        </div>
      </div>
    </>
  )
}
