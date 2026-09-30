// Тарифы для лендинга и страницы /methods.
// Содержимое карточек редактируется в админке (/admin/pricing) и приходит
// из GET /api/pricing. Дефолты ниже нужны только на случай, если API
// недоступен во время рендера.

export interface PricingData {
  title: string
  price: number
  currency: string
  description: string
  features: { label: string; value: string }[]
}

export const DEFAULT_PRICING: PricingData = {
  title: 'Полный отчёт 64 ДАО',
  price: 14900,
  currency: '₽',
  description: 'разовая оплата · НДС не облагается',
  features: [
    { label: 'Диагностика', value: 'Метод 1 + Метод 2' },
    { label: 'PDF-отчёт', value: 'Включён' },
    { label: 'Онлайн-просмотр', value: 'Без ограничений' },
    { label: 'Срок готовности', value: 'До 30 минут' },
  ],
}

export const DEFAULT_PRICING_M3: PricingData = {
  title: 'Матрица силы · Метод 3 + Алмазное колесо · Метод 4',
  price: 20000,
  currency: '₽',
  description: 'разовая оплата · НДС не облагается',
  features: [
    { label: 'Диагностика', value: 'Метод 3 + Метод 4' },
    { label: 'Направлений в портфеле', value: 'От 3 до 8' },
    { label: 'PDF-отчёт', value: 'Включён' },
    { label: 'Онлайн-просмотр', value: 'Без ограничений' },
  ],
}

function merge(src: any, def: PricingData): PricingData {
  return {
    title: src?.title ?? def.title,
    price: src?.price ?? def.price,
    currency: src?.currency ?? def.currency,
    description: src?.description ?? def.description,
    features: Array.isArray(src?.features) && src.features.length > 0 ? src.features : def.features,
  }
}

// Один запрос на оба тарифа. Next дедуплицирует одинаковые fetch в пределах
// рендера, так что вызов из двух мест не даёт второго похода в сеть.
async function fetchPricingRaw(): Promise<any | null> {
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? ''
    const res = await fetch(`${apiUrl}/api/pricing`, { next: { revalidate: 300 } })
    if (res.ok) return await res.json()
  } catch {
    // дефолт ниже
  }
  return null
}

export async function getPricing(): Promise<PricingData> {
  const data = await fetchPricingRaw()
  return data ? merge(data, DEFAULT_PRICING) : DEFAULT_PRICING
}

export async function getPricingM3(): Promise<PricingData> {
  const data = await fetchPricingRaw()
  const m3 = data?.products?.m3
  return m3 ? merge(m3, DEFAULT_PRICING_M3) : DEFAULT_PRICING_M3
}

export function formatPrice(p: PricingData): string {
  return p.price.toLocaleString('ru-RU')
}
