import type { Metadata } from 'next'
import AboutShell from '@/components/AboutShell'
import LandingFonts from '@/components/LandingFonts'
import JsonLd from '@/components/JsonLd'

export const metadata: Metadata = {
  title: 'О нас — 64 ДАО',
  description: 'Команда 64 ДАО: методика на основе «И-цзин», 20 лет консультирования, более 100 научных исследований.',
}

export default async function AboutPage() {
  let htmlContent = ''

  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? ''
    const res = await fetch(`${apiUrl}/api/documents/about`, {
      next: { revalidate: 3600 },
    })
    if (res.ok) {
      // API возвращает JSON { slug, title, content, published, updated_at },
      // а не сырой HTML — нужно достать поле content.
      const data = await res.json()
      if (data.published) {
        htmlContent = data.content ?? ''
      }
    }
  } catch {
    // Контент придёт пустым; AboutShell отрендерит обёртку без него
  }

  const aboutSchema = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: '64 ДАО',
    url: 'https://64dao.ru',
    logo: 'https://64dao.ru/assets/logo.svg',
    description:
      'Стратегическая диагностика бизнеса на основе «И-цзин»: определяет фазу компании, уместные управленческие решения, служит опорой для стратегических сессий.',
  }

  return (
    <>
      <JsonLd data={aboutSchema} />
      <LandingFonts />
      <AboutShell htmlContent={htmlContent} />
    </>
  )
}
