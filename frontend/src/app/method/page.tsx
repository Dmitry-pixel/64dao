import type { Metadata } from 'next'
import JsonLd from '@/components/JsonLd'
import LandingFonts from '@/components/LandingFonts'
import MethodShell from '@/components/MethodShell'
import { METHOD_ARTICLES, METHOD_LAST_UPDATED } from '@/lib/methodArticles'

// Страница полностью статическая: контент лежит в TS-модуле, запросов к API нет.
export const dynamic = 'force-static'

export const metadata: Metadata = {
  title: 'Методика 64 ДАО — как устроена диагностика фазы компании',
  description:
    'Пять статей о том, как определяется стадия жизненного цикла компании, как находится системное ограничение и чем диагностика фазы отличается от SWOT и Business Model Canvas.',
  alternates: { canonical: 'https://64dao.ru/method' },
  openGraph: {
    type: 'website',
    url: 'https://64dao.ru/method',
    title: 'Методика 64 ДАО',
    description:
      'Как определяется стадия жизненного цикла компании и как находится системное ограничение.',
  },
}

export default function MethodIndexPage() {
  const collectionSchema = {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    '@id': 'https://64dao.ru/method#collection',
    name: 'Методика 64 ДАО',
    description: metadata.description,
    url: 'https://64dao.ru/method',
    inLanguage: 'ru-RU',
    isPartOf: { '@id': 'https://64dao.ru/#webpage' },
    publisher: { '@id': 'https://64dao.ru/#organization' },
    about: { '@id': 'https://64dao.ru/#software' },
    dateModified: METHOD_LAST_UPDATED,
    // hasPart связывает раздел со статьями по @id — так ассистент понимает,
    // что это связанный корпус, а не пять независимых страниц.
    hasPart: METHOD_ARTICLES.map((a) => ({
      '@type': 'TechArticle',
      '@id': `https://64dao.ru/method/${a.slug}#article`,
      headline: a.title,
      url: `https://64dao.ru/method/${a.slug}`,
    })),
  }

  const breadcrumbSchema = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Главная', item: 'https://64dao.ru' },
      { '@type': 'ListItem', position: 2, name: 'Методика', item: 'https://64dao.ru/method' },
    ],
  }

  return (
    <>
      <JsonLd data={collectionSchema} />
      <JsonLd data={breadcrumbSchema} />
      <LandingFonts />
      <MethodShell>
        <div className="method-article">
          <nav className="method-crumbs" aria-label="Хлебные крошки">
            <a href="/">Главная</a>
            <span aria-hidden="true">/</span>
            <span>Методика</span>
          </nav>

          <h1 className="method-h1">Методика 64 ДАО</h1>

          <p className="method-lead">
            Диагностика 64 ДАО определяет не «что у компании плохо», а в какой фазе она
            находится и что из-за этого преждевременно. Здесь собрано, как это устроено:
            откуда берутся 64 состояния, как измеряется зрелость функций, как находится
            узкое место и чем такой подход отличается от SWOT и Business Model Canvas.
          </p>

          <ul className="method-index">
            {METHOD_ARTICLES.map((a) => (
              <li key={a.slug}>
                <a href={`/method/${a.slug}`}>
                  <span className="method-index-title">{a.title}</span>
                  <span className="method-index-desc">{a.description}</span>
                </a>
              </li>
            ))}
          </ul>

          <aside className="method-cta">
            <h2 className="method-cta-h">Проверить это на своей компании</h2>
            <p className="method-p">
              Диагностика занимает около 15 минут. На выходе — отчёт со стадией цикла,
              системным ограничением и маршрутом перехода.
            </p>
            <a href="/login" className="method-cta-btn">
              Пройти диагностику
            </a>
          </aside>
        </div>
      </MethodShell>
    </>
  )
}
