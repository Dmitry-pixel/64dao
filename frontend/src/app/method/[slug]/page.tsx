import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import JsonLd from '@/components/JsonLd'
import LandingFonts from '@/components/LandingFonts'
import MethodShell from '@/components/MethodShell'
import MethodArticle from '@/components/MethodArticle'
import { METHOD_ARTICLES, getArticle } from '@/lib/methodArticles'

// generateStaticParams обязателен: без него динамический сегмент уходит в
// force-dynamic, ответ получает Cache-Control: private, no-store, и страница
// не индексируется. Тот же приём уже применён в hexagram/[combination].
export function generateStaticParams() {
  return METHOD_ARTICLES.map((a) => ({ slug: a.slug }))
}

// Несуществующий слаг должен отдавать 404, а не рендериться на лету.
export const dynamicParams = false

type Params = { slug: string }

export function generateMetadata({ params }: { params: Params }): Metadata {
  const a = getArticle(params.slug)
  if (!a) return { title: 'Статья не найдена — 64 ДАО' }

  const url = `https://64dao.ru/method/${a.slug}`
  return {
    title: `${a.title} — 64 ДАО`,
    description: a.description,
    alternates: { canonical: url },
    authors: [{ name: 'Дмитрий Подласов' }],
    openGraph: {
      type: 'article',
      url,
      title: a.title,
      description: a.description,
      publishedTime: a.datePublished,
      modifiedTime: a.dateModified,
    },
  }
}

export default function MethodArticlePage({ params }: { params: Params }) {
  const a = getArticle(params.slug)
  if (!a) notFound()

  const url = `https://64dao.ru/method/${a.slug}`

  // Узлы #organization и #software уже объявлены в графе лендинга
  // (src/app/page.tsx). Здесь на них только ссылаемся по @id — дублировать
  // определения нельзя, иначе граф разъедется.
  const articleSchema = {
    '@context': 'https://schema.org',
    '@type': 'TechArticle',
    '@id': `${url}#article`,
    headline: a.title,
    description: a.description,
    datePublished: a.datePublished,
    dateModified: a.dateModified,
    inLanguage: 'ru-RU',
    author: {
      '@type': 'Person',
      name: 'Дмитрий Подласов',
      jobTitle: 'Автор методики 64 ДАО',
    },
    publisher: { '@id': 'https://64dao.ru/#organization' },
    about: { '@id': 'https://64dao.ru/#software' },
    isPartOf: { '@id': 'https://64dao.ru/method#collection' },
    mainEntityOfPage: url,
  }

  const breadcrumbSchema = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Главная', item: 'https://64dao.ru' },
      { '@type': 'ListItem', position: 2, name: 'Методика', item: 'https://64dao.ru/method' },
      { '@type': 'ListItem', position: 3, name: a.title, item: url },
    ],
  }

  return (
    <>
      <JsonLd data={articleSchema} />
      <JsonLd data={breadcrumbSchema} />
      <LandingFonts />
      <MethodShell>
        <MethodArticle article={a} />
      </MethodShell>
    </>
  )
}
