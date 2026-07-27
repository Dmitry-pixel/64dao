// Страница описания гексаграммы: /hexagram/{combination}?from=/report/{id}
//
// generateStaticParams обязателен: без него динамический сегмент уходит в
// force-dynamic и отдаёт Cache-Control: private, no-store, что блокирует обход
// поисковиками. dynamicParams = false даёт 404 на комбинациях вне списка 64.
//
// Содержимое под авторизацией, поэтому его грузит клиентский HexagramDetail.
// Он использует useSearchParams, а это в статически генерируемой странице
// требует обёртки в Suspense, иначе сборка Next 14 падает.
import { Suspense } from 'react'
import { HEXAGRAM_DATA } from '@/lib/hexagrams'
import HexagramDetail from '@/components/HexagramDetail'

export const dynamicParams = false

export function generateStaticParams() {
  return HEXAGRAM_DATA.map((h) => ({ combination: h.combo }))
}

export const metadata = {
  title: 'Описание гексаграммы — 64dao',
}

export default function HexagramPage({ params }: { params: { combination: string } }) {
  return (
    <Suspense fallback={null}>
      <HexagramDetail combination={params.combination.toUpperCase()} />
    </Suspense>
  )
}
