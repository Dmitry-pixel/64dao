'use client'

import { useEffect, useRef, useState } from 'react'

function Hexagram({ seed }: { seed: number }) {
  const lines = Array.from({ length: 6 }, (_, i) => ((seed * 7 + i * 13) % 3) !== 0)
  return (
    <svg
      viewBox="0 0 40 40"
      preserveAspectRatio="xMidYMid meet"
      style={{ height: '100%', width: '100%' }}
    >
      {lines.map((solid, i) => {
        const y = 4.8 + i * 5.6
        return solid ? (
          <rect key={i} x={4} y={y} width={32} height={2.4} rx={0.6} fill="currentColor" />
        ) : (
          <g key={i} fill="currentColor">
            <rect x={4}  y={y} width={13} height={2.4} rx={0.6} />
            <rect x={23} y={y} width={13} height={2.4} rx={0.6} />
          </g>
        )
      })}
    </svg>
  )
}

function HexMatrix({ containerWidth }: { containerWidth: number }) {
  const TILE   = 56
  const GAP    = 12
  const PERIOD = 68
  const RED    = 12

  const w  = (containerWidth || 1040) - 40
  const to = w / 2 - (RED * PERIOD + TILE / 2)

  const rows = [
    { from:  520, off: 0, exit:  160 },
    { from: -640, off: 7, exit: -200 },
    { from:  760, off: 3, exit:  220 },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {rows.map((r, ri) => {
        const tiles = Array.from({ length: 26 }, (_, i) => i + r.off)
        return (
          <div key={ri} style={{ position: 'relative' }}>
            <div style={{ position: 'relative', overflow: 'hidden' }}>
              <div
                style={
                  {
                    display: 'flex',
                    gap: GAP,
                    width: 'max-content',
                    animation: 'hex-shuttle 22s cubic-bezier(.42,0,.58,1) infinite',
                    '--from': r.from + 'px',
                    '--to':   to     + 'px',
                    transform: 'translateX(' + r.from + 'px)',
                  } as React.CSSProperties
                }
              >
                {tiles.map((seed, i) => {
                  const isRed = i === RED
                  return (
                    <div
                      key={i}
                      style={{
                        height: TILE,
                        width:  TILE,
                        flexShrink: 0,
                        color: isRed
                          ? 'var(--accent)'
                          : 'color-mix(in oklab, var(--foreground) 70%, transparent)',
                      }}
                    >
                      <Hexagram seed={isRed ? 42 : seed} />
                    </div>
                  )
                })}
              </div>
            </div>

            <div
              style={
                {
                  position: 'absolute',
                  top: 0,
                  left: '50%',
                  height: TILE,
                  width:  TILE,
                  borderRadius: 2,
                  border: '2px solid var(--accent)',
                  pointerEvents: 'none',
                  animation: 'hex-stop-shard 22s ease-in-out infinite',
                  '--exit': r.exit + 'px',
                  boxShadow: '0 0 0 4px color-mix(in oklab, var(--accent) 12%, transparent)',
                } as React.CSSProperties
              }
            />
          </div>
        )
      })}
    </div>
  )
}

function YinYang() {
  return (
    <svg viewBox="0 0 200 200" aria-hidden style={{ height: '100%', width: '100%' }}>
      <defs>
        <clipPath id="yy-clip">
          <circle cx={100} cy={100} r={96} />
        </clipPath>
      </defs>
      <g clipPath="url(#yy-clip)">
        <circle cx={100} cy={100} r={96} fill="currentColor" opacity={0.06} />
        <path
          d="M100 4a96 96 0 0 0 0 192 48 48 0 0 0 0-96 48 48 0 0 1 0-96z"
          fill="currentColor"
          opacity={0.16}
        />
        <circle cx={100} cy={52}  r={10} fill="currentColor" opacity={0.22} />
        <circle cx={100} cy={148} r={10} fill="none" stroke="currentColor" strokeOpacity={0.22} strokeWidth={2} />
      </g>
      <circle cx={100} cy={100} r={96} fill="none" stroke="currentColor" strokeOpacity={0.18} strokeWidth={1.5} />
    </svg>
  )
}

export default function HeroSection() {
  const yinRef    = useRef<HTMLDivElement>(null)
  const matrixRef = useRef<HTMLDivElement>(null)
  const [rowWidth, setRowWidth] = useState(1040)

  useEffect(() => {
    const measure = () => {
      if (matrixRef.current) {
        setRowWidth(matrixRef.current.clientWidth)
      }
    }
    requestAnimationFrame(measure)
    window.addEventListener('resize', measure)

    const onScroll = () => {
      if (yinRef.current) {
        const y = window.scrollY
        yinRef.current.style.transform =
          'translateY(calc(-50% + ' + (y * 0.15) + 'px)) rotate(' + (y * 0.08) + 'deg)'
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true })

    return () => {
      window.removeEventListener('resize', measure)
      window.removeEventListener('scroll', onScroll)
    }
  }, [])

  return (
    <section
      id="top"
      style={{ position: 'relative', overflow: 'hidden', borderBottom: '1px solid rgba(0,0,0,0.06)' }}
    >
      <div
        ref={yinRef}
        style={{
          pointerEvents: 'none',
          position: 'absolute',
          left: -128,
          top: '62%',
          transform: 'translateY(-50%)',
          zIndex: 0,
          height: 720,
          width: 720,
          color: 'var(--foreground)',
          willChange: 'transform',
        }}
      >
        <YinYang />
      </div>

      <div
        style={{
          position: 'relative',
          zIndex: 10,
          maxWidth: 1280,
          margin: '0 auto',
          display: 'grid',
          gridTemplateColumns: '1.35fr 1fr',
          alignItems: 'center',
          gap: 48,
          padding: '112px 40px',
        }}
      >
        <div style={{ minWidth: 0 }}>
          <h1
            style={{
              margin: 0,
              fontFamily: "'Golos Text',sans-serif",
              fontWeight: 700,
              fontSize: 'clamp(34px,4.6vw,60px)',
              lineHeight: 1.12,
              letterSpacing: '-0.01em',
              color: 'var(--foreground)',
            }}
          >
            «И-цзин» для разработки и управления стратегией изменений компании
          </h1>
          <div style={{ marginTop: 32, height: 3, width: 80, background: 'var(--accent)' }} />
          <p
            style={{
              marginTop: 32,
              maxWidth: 640,
              fontSize: 18,
              lineHeight: 1.6,
              color: 'color-mix(in oklab, var(--foreground) 80%, transparent)',
            }}
          >
            64 ДАО — инструмент стратегического диагностирования, основанный на метафизике «И-цзин».
            Определяет, в какой фазе находится компания, какие управленческие решения уместны сейчас,
            и служит опорой при проведении стратегических сессий.
          </p>
          <div style={{ marginTop: 40, display: 'flex', flexWrap: 'wrap', gap: 16 }}>
            <a href="/login"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                borderRadius: 2,
                background: 'var(--accent)',
                padding: '14px 24px',
                fontSize: 14,
                fontWeight: 500,
                color: 'var(--accent-foreground)',
                textDecoration: 'none',
              }}
            >
              Пройти диагностику <span aria-hidden="true">→</span>
            </a>
            <a href="/api/sample-report"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: 2,
                background: 'var(--foreground)',
                padding: '14px 24px',
                fontSize: 14,
                fontWeight: 500,
                color: 'var(--background)',
                textDecoration: 'none',
              }}
            >
              Посмотреть пример отчёта
            </a>
          </div>
        </div>

        <div style={{ minWidth: 0 }}>
          <div style={{ position: 'relative' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: 10,
                fontWeight: 500,
                textTransform: 'uppercase',
                letterSpacing: '0.24em',
                color: 'var(--muted-foreground)',
              }}
            >
              <span>идёт выборка</span>
              <span>64 фазы</span>
            </div>
            <div
              ref={matrixRef}
              style={{
                position: 'relative',
                marginTop: 20,
                borderRadius: 2,
                border: '1px solid var(--border)',
                background: 'color-mix(in oklab, var(--card) 60%, transparent)',
                padding: 20,
                boxShadow: '0 30px 80px -40px rgba(20,30,60,0.35)',
                overflow: 'hidden',
              }}
            >
              <HexMatrix containerWidth={rowWidth} />
              <div style={{ pointerEvents: 'none', position: 'absolute', top: 20, bottom: 20, left: 20, width: 64, background: 'linear-gradient(to right, var(--card), transparent)' }} />
              <div style={{ pointerEvents: 'none', position: 'absolute', top: 20, bottom: 20, right: 20, width: 64, background: 'linear-gradient(to left, var(--card), transparent)' }} />
            </div>
            <div
              style={{
                marginTop: 20,
                display: 'flex',
                alignItems: 'flex-end',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.24em', color: 'var(--accent)' }}>
                  Фаза роста
                </div>
                <div style={{ marginTop: 4, fontSize: 14, color: 'var(--foreground)' }}>11 / 64 · ваша фаза</div>
              </div>
              <span style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>пример результата</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
