import type { Block, MethodArticle as Article } from '@/lib/methodArticles'
import { METHOD_ARTICLES } from '@/lib/methodArticles'

/**
 * Рендер одной статьи раздела /method. Server Component.
 *
 * Все блоки статьи выводятся сразу, без сворачивания и без состояния:
 * контент за useState не попадает в SSR-HTML. Если когда-нибудь понадобится
 * сворачивание — только через <details>/<summary>, как в FaqSection.
 */

function renderBlock(b: Block, i: number) {
  switch (b.t) {
    case 'p':
      return (
        <p key={i} className="method-p">
          {b.text}
        </p>
      )

    case 'quote':
      // Цитата видима как цитата и имеет видимую атрибуцию — требование
      // как разметки, так и честности перед читателем.
      return (
        <figure key={i} className="method-quote">
          <blockquote>{'«' + b.text + '»'}</blockquote>
          <figcaption>
            <cite>{b.cite}</cite>
          </figcaption>
        </figure>
      )

    case 'list':
      return (
        <ul key={i} className="method-ul">
          {b.items.map((it, k) => (
            <li key={k}>{it}</li>
          ))}
        </ul>
      )

    case 'table':
      return (
        <div key={i} className="method-tablewrap">
          <table className="method-table">
            <thead>
              <tr>
                {b.head.map((h, k) => (
                  <th key={k} scope="col">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {b.rows.map((row, k) => (
                <tr key={k}>
                  {row.map((cell, m) => (
                    <td key={m}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
  }
}

function formatDate(iso: string) {
  const MONTHS = [
    'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
  ]
  const [y, m, d] = iso.split('-').map(Number)
  return `${d} ${MONTHS[m - 1]} ${y} г.`
}

export default function MethodArticle({ article }: { article: Article }) {
  const others = METHOD_ARTICLES.filter((a) => a.slug !== article.slug)

  return (
    <article className="method-article">
      <nav className="method-crumbs" aria-label="Хлебные крошки">
        <a href="/">Главная</a>
        <span aria-hidden="true">/</span>
        <a href="/method">Методика</a>
      </nav>

      <h1 className="method-h1">{article.h1}</h1>

      <div className="method-meta">
        <span>Дмитрий Подласов, автор методики 64 ДАО</span>
        <span aria-hidden="true">·</span>
        <time dateTime={article.dateModified}>{formatDate(article.dateModified)}</time>
      </div>

      {/* Прямой ответ на вопрос заголовка. Именно этот абзац извлекают
          ассистенты, поэтому он идёт до любых подзаголовков. */}
      <p className="method-lead">{article.lead}</p>

      {article.sections.map((s, i) => (
        <section key={i} className="method-section">
          <h2 className="method-h2">{s.h}</h2>
          {s.blocks.map(renderBlock)}
        </section>
      ))}

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

      <nav className="method-more" aria-label="Другие статьи раздела">
        <h2 className="method-h2">Ещё в разделе</h2>
        <ul className="method-ul">
          {others.map((a) => (
            <li key={a.slug}>
              <a href={`/method/${a.slug}`}>{a.title}</a>
            </li>
          ))}
        </ul>
      </nav>
    </article>
  )
}
