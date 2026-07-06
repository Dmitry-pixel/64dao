import type { Metadata } from 'next'
import LegalShell from '@/components/LegalShell'
import LandingFonts from '@/components/LandingFonts'
import JsonLd from '@/components/JsonLd'

// ─── Мета-данные по slug ──────────────────────────────────────────────────────

const TITLES: Record<string, string> = {
  'privacy-policy':       'Политика обработки персональных данных',
  'user-agreement':       'Пользовательское соглашение',
  'personal-data-consent': 'Согласие на обработку персональных данных',
}

export function generateStaticParams() {
  return Object.keys(TITLES).map((slug) => ({ slug }))
}

type Params = { slug: string }

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const title = TITLES[params.slug] ?? 'Правовой документ'
  return {
    title: `${title} — 64 ДАО`,
    description: `${title}. Сайт 64dao.ru. Редакция от 26 июня 2026 г.`,
  }
}

// ─── Страница ─────────────────────────────────────────────────────────────────

export default async function DocumentPage({ params }: { params: Params }) {
  let htmlContent = ''
  let apiTitle: string | null = null

  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? ''
    const res = await fetch(`${apiUrl}/api/documents/${params.slug}`, {
      next: { revalidate: 60 },
    })
    if (res.ok) {
      // API возвращает JSON { slug, title, content, published, updated_at },
      // а не сырой HTML — нужно достать поле content.
      const data = await res.json()
      if (data.published) {
        htmlContent = data.content ?? ''
      }
      apiTitle = data.title ?? null
    }
  } catch {
    // Контент придёт пустым; LegalShell отрендерит обёртку без него
  }

  const title = apiTitle ?? TITLES[params.slug] ?? 'Правовой документ'

  const breadcrumbSchema = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      {
        '@type': 'ListItem',
        position: 1,
        name: 'Главная',
        item: 'https://64dao.ru',
      },
      {
        '@type': 'ListItem',
        position: 2,
        name: title,
        item: `https://64dao.ru/documents/${params.slug}`,
      },
    ],
  }

  return (
    <>
      <JsonLd data={breadcrumbSchema} />
      <LandingFonts />
      <LegalShell
        slug={params.slug}
        title={title}
        htmlContent={htmlContent}
      />
    </>
  )
}
