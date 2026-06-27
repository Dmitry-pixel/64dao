'use client';

import { useEffect, useRef, useState } from 'react';

// ── Гексаграмма (6 линий, сплошная/прерывистая) ──────────────────────
function Hexagram({ seed, className }: { seed: number; className?: string }) {
  const lines = Array.from({ length: 6 }, (_, i) => ((seed * 7 + i * 13) % 3) !== 0);
  return (
    <svg viewBox="0 0 40 40" preserveAspectRatio="xMidYMid meet" className={className} style={{ height: '100%', width: '100%' }}>
      {lines.map((solid, i) => {
        const y = 4.8 + i * 5.6;
        return solid ? (
          <rect key={i} x={4} y={y} width={32} height={2.4} rx={0.6} fill="currentColor" />
        ) : (
          <g key={i} fill="currentColor">
            <rect x={4} y={y} width={13} height={2.4} rx={0.6} />
            <rect x={23} y={y} width={13} height={2.4} rx={0.6} />
          </g>
        );
      })}
    </svg>
  );
}

// ── Бегущая матрица гексаграмм (Hero) ─────────────────────────────────
export function HexMatrix() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [rowWidth, setRowWidth] = useState(1040);

  useEffect(() => {
    const measure = () => {
      if (containerRef.current) setRowWidth(containerRef.current.clientWidth);
    };
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, []);

  const TILE = 56, GAP = 12, PERIOD = 68, RED = 12;
  const w = rowWidth - 40;
  const rows = [
    { from: 520, off: 0, exit: 160 },
    { from: -640, off: 7, exit: -200 },
    { from: 760, off: 3, exit: 220 },
  ];
  const redCenter = RED * PERIOD + TILE / 2;
  const to = w / 2 - redCenter;

  return (
    <div
      ref={containerRef}
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
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {rows.map((r, ri) => {
          const tiles = Array.from({ length: 26 }, (_, i) => i + r.off);
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
                      '--to': to + 'px',
                      transform: 'translateX(' + r.from + 'px)',
                    } as React.CSSProperties
                  }
                >
                  {tiles.map((seed, i) => {
                    const isRed = i === RED;
                    return (
                      <div
                        key={i}
                        style={{
                          height: 56,
                          width: 56,
                          flexShrink: 0,
                          color: isRed ? 'var(--accent)' : 'color-mix(in oklab, var(--foreground) 70%, transparent)',
                        }}
                      >
                        <Hexagram seed={isRed ? 42 : seed} />
                      </div>
                    );
                  })}
                </div>
              </div>
              <div
                style={
                  {
                    position: 'absolute',
                    top: 0,
                    left: '50%',
                    height: 56,
                    width: 56,
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
          );
        })}
      </div>
      <div
        style={{
          pointerEvents: 'none',
          position: 'absolute',
          top: 20,
          bottom: 20,
          left: 20,
          width: 64,
          background: 'linear-gradient(to right, var(--card), transparent)',
        }}
      />
      <div
        style={{
          pointerEvents: 'none',
          position: 'absolute',
          top: 20,
          bottom: 20,
          right: 20,
          width: 64,
          background: 'linear-gradient(to left, var(--card), transparent)',
        }}
      />
    </div>
  );
}

// ── Инь-Янь фоновая фигура (Hero, параллакс при скролле) ─────────────
export function YinYang() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onScroll = () => {
      if (ref.current) {
        const y = window.scrollY;
        ref.current.style.transform = `translateY(calc(-50% + ${y * 0.15}px)) rotate(${y * 0.08}deg)`;
      }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div
      ref={ref}
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
          <circle cx={100} cy={52} r={10} fill="currentColor" opacity={0.22} />
          <circle cx={100} cy={148} r={10} fill="none" stroke="currentColor" strokeOpacity={0.22} strokeWidth={2} />
        </g>
        <circle cx={100} cy={100} r={96} fill="none" stroke="currentColor" strokeOpacity={0.18} strokeWidth={1.5} />
      </svg>
    </div>
  );
}

// ── Кривая жизненного цикла (секция «Что в отчёте») ───────────────────
export function CycleCurve() {
  const labels = [
    { x: 70, l: 'ЗАРОЖДЕНИЕ' },
    { x: 220, l: 'РОСТ', bold: true },
    { x: 380, l: 'ЗРЕЛОСТЬ' },
    { x: 530, l: 'СПАД' },
  ];
  return (
    <svg viewBox="0 0 600 220" style={{ height: 'auto', width: '100%' }}>
      <path
        d="M10 180 C 80 180, 130 60, 220 60 C 310 60, 340 200, 430 200 C 500 200, 540 100, 590 80"
        fill="none"
        stroke="oklch(0.28 0.08 260)"
        strokeWidth={2.2}
        strokeLinecap="round"
      />
      <path
        d="M590 80 L 596 78"
        fill="none"
        stroke="oklch(0.28 0.08 260)"
        strokeWidth={2}
        strokeDasharray="3 4"
      />
      <circle cx={220} cy={60} r={18} fill="oklch(0.28 0.08 260)" opacity={0.08} />
      <circle cx={220} cy={60} r={6} fill="var(--accent)" />
      <text x={220} y={36} textAnchor="middle" fontSize={11} fill="var(--accent)" style={{ letterSpacing: '0.18em' }}>
        ВЫ ЗДЕСЬ
      </text>
      <line x1={10} y1={200} x2={590} y2={200} stroke="oklch(0.86 0.02 92)" />
      {labels.map((t) => (
        <text
          key={t.l}
          x={t.x}
          y={216}
          textAnchor="middle"
          fontSize={10}
          fill={t.bold ? 'oklch(0.16 0.03 260)' : 'oklch(0.45 0.03 260)'}
          fontWeight={t.bold ? 600 : 400}
          style={{ letterSpacing: '0.18em' }}
        >
          {t.l}
        </text>
      ))}
    </svg>
  );
}

// ── Шкала «инвестировать / подождать» ─────────────────────────────────
export function Gauge() {
  const cx = 100, cy = 100, r = 78;
  return (
    <svg viewBox="0 0 200 130" style={{ height: 'auto', width: '100%', maxWidth: 220 }}>
      <path
        d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx - r * 0.31} ${cy - r * 0.95}`}
        fill="none"
        stroke="oklch(0.6 0.22 27)"
        strokeWidth={14}
      />
      <path
        d={`M ${cx - r * 0.31} ${cy - r * 0.95} A ${r} ${r} 0 0 1 ${cx + r * 0.31} ${cy - r * 0.95}`}
        fill="none"
        stroke="oklch(0.78 0.16 75)"
        strokeWidth={14}
      />
      <path
        d={`M ${cx + r * 0.31} ${cy - r * 0.95} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
        fill="none"
        stroke="oklch(0.55 0.13 160)"
        strokeWidth={14}
      />
      <g transform={`rotate(40 ${cx} ${cy})`}>
        <line x1={cx} y1={cy} x2={cx + r - 8} y2={cy} stroke="oklch(0.16 0.03 260)" strokeWidth={3} strokeLinecap="round" />
      </g>
      <circle cx={cx} cy={cy} r={6} fill="oklch(0.16 0.03 260)" />
    </svg>
  );
}

// ── Точки оценки (1-5) для блоков бизнес-модели ───────────────────────
export function Dots({ value, tone }: { value: number; tone: 'ok' | 'warn' | 'alert' }) {
  const tc = tone === 'alert' ? 'var(--accent)' : tone === 'warn' ? 'oklch(0.78 0.16 75)' : 'oklch(0.55 0.13 160)';
  return (
    <div style={{ display: 'flex', gap: 4 }}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span
          key={i}
          style={{
            height: 8,
            width: 8,
            borderRadius: '9999px',
            background: i <= value ? tc : 'var(--muted)',
          }}
        />
      ))}
    </div>
  );
}
