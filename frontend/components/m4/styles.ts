/**
 * Метод 4 — общие стили страниц анкеты и результата.
 * Палитра и типографика — те же, что у страниц Метода 3 (/m3): один продукт,
 * один вид.
 */
import type { CSSProperties } from 'react'

const INK = '#1a2540'
const RED = '#c0392b'

const optBase: CSSProperties = {
  padding: '9px 16px', borderRadius: 6, fontFamily: 'sans-serif', fontSize: 14,
  cursor: 'pointer', border: '1px solid rgba(26,37,64,0.2)', background: '#fff', color: INK,
}
const choiceBase: CSSProperties = {
  ...optBase, textAlign: 'left', padding: '14px 18px', minWidth: 240, lineHeight: 1.5,
}

export const M4 = {
  page: { minHeight: '100vh', background: '#e8e4db' } as CSSProperties,
  stage: { maxWidth: 860, margin: '0 auto', padding: '56px 40px' } as CSSProperties,
  label: {
    fontFamily: 'sans-serif', fontSize: 11, letterSpacing: 2,
    textTransform: 'uppercase', color: RED, fontWeight: 600,
  } as CSSProperties,
  h1: { fontFamily: 'Georgia,serif', fontSize: 34, fontWeight: 400, color: INK, margin: '10px 0 12px' } as CSSProperties,
  h2: { fontFamily: 'Georgia,serif', fontSize: 24, fontWeight: 400, color: INK, margin: '0 0 6px' } as CSSProperties,
  text: {
    fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.65)',
    lineHeight: 1.7, marginBottom: 18, maxWidth: 620,
  } as CSSProperties,
  muted: { fontFamily: 'sans-serif', fontSize: 14, color: 'rgba(26,37,64,0.6)' } as CSSProperties,
  field: { display: 'flex', flexDirection: 'column', gap: 5, maxWidth: 420 } as CSSProperties,
  fieldLabel: { fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.6)' } as CSSProperties,
  input: {
    padding: '9px 11px', border: '1px solid rgba(26,37,64,0.2)', borderRadius: 6,
    fontFamily: 'sans-serif', fontSize: 14, color: INK, background: '#fff',
    width: '100%', boxSizing: 'border-box',
  } as CSSProperties,
  btnPrimary: {
    display: 'inline-flex', alignItems: 'center', gap: 8, padding: '11px 22px',
    background: INK, color: '#fff', border: 'none', borderRadius: 6,
    fontFamily: 'sans-serif', fontSize: 14, cursor: 'pointer',
  } as CSSProperties,
  btnGhost: {
    padding: '11px 18px', background: 'none', border: '1px solid rgba(26,37,64,0.2)',
    borderRadius: 6, fontFamily: 'sans-serif', fontSize: 14, cursor: 'pointer', color: INK,
  } as CSSProperties,
  warn: { fontFamily: 'sans-serif', fontSize: 13, color: RED, lineHeight: 1.6 } as CSSProperties,
  note: { fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.5)', lineHeight: 1.6, marginTop: 10 } as CSSProperties,
  listRow: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    gap: 12, padding: '11px 0', borderBottom: '1px solid rgba(26,37,64,0.08)',
    fontFamily: 'sans-serif', fontSize: 14, color: INK,
  } as CSSProperties,
  status: { fontFamily: 'sans-serif', fontSize: 12, color: 'rgba(26,37,64,0.5)' } as CSSProperties,
  opt: optBase,
  optOn: { ...optBase, background: INK, color: '#fff', border: `1px solid ${INK}` } as CSSProperties,
  optUnknown: { ...optBase, color: 'rgba(26,37,64,0.6)', border: '1px dashed rgba(26,37,64,0.3)' } as CSSProperties,
  optUnknownOn: { ...optBase, background: 'rgba(26,37,64,0.55)', color: '#fff', border: '1px solid transparent' } as CSSProperties,
  choice: choiceBase,
  choiceOn: { ...choiceBase, border: `1px solid ${INK}`, boxShadow: `inset 0 0 0 1px ${INK}` } as CSSProperties,
  choiceNote: { fontSize: 12, color: 'rgba(26,37,64,0.6)' } as CSSProperties,
  card: {
    background: '#fff', borderRadius: 8, padding: '20px 22px', marginBottom: 14,
    boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
  } as CSSProperties,
  qText: { fontFamily: 'sans-serif', fontSize: 15, color: INK, lineHeight: 1.55, margin: '0 0 12px' } as CSSProperties,
}

export const STATE_COLOR: Record<string, string> = { low: RED, mid: '#c8902a', high: '#2e7d5b' }
export const STATE_LABEL: Record<string, string> = { low: 'низкий', mid: 'средний', high: 'высокий' }
