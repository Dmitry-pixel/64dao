'use client'
import { useState, type CSSProperties, type ReactNode } from 'react'
import SampleReportModal, { type SampleDoc } from '@/components/SampleReportModal'

/**
 * Кнопка, открывающая форму перед скачиванием документа.
 *
 * Нужна потому, что лендинг (`app/page.tsx`) — Server Component: обработчик
 * onClick туда положить нельзя, а раньше там стояли прямые ссылки на
 * /api/sample-report — они отдавали файл мимо формы, и лид терялся.
 *
 * Стиль передаётся снаружи: на лендинге эта кнопка стоит в трёх местах с
 * разным оформлением, и заводить три варианта компонента ради этого незачем.
 */
export default function SampleReportButton({
  method,
  children,
  style,
  className,
}: {
  method: SampleDoc
  children: ReactNode
  style?: CSSProperties
  className?: string
}) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        className={className}
        onClick={() => setOpen(true)}
        style={{ border: 'none', cursor: 'pointer', font: 'inherit', ...style }}
      >
        {children}
      </button>
      <SampleReportModal open={open} onClose={() => setOpen(false)} method={method} />
    </>
  )
}
