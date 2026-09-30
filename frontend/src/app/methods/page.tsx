import type { Metadata } from 'next'
import Link from 'next/link'
import '../landing-b.css'
import SiteNav from '@/components/SiteNav'
import SiteFooter from '@/components/SiteFooter'
import CookieBanner from '@/components/CookieBanner'
import LandingFonts from '@/components/LandingFonts'
import JsonLd from '@/components/JsonLd'
import SampleReportButton from '@/components/SampleReportButton'
import { PowerMatrixSvg, DiamondWheelSvg } from '@/components/MethodDiagrams'
import { getPricingM3, formatPrice } from '@/lib/landingPricing'

// Тексты и схемы перенесены с прежней главной (блоки «Матрица силы · Метод 3»,
// «Алмазное колесо · Метод 4», «Стоимость · Метод 3»).

const TITLE = 'Матрица силы и Алмазное колесо — Методы 3 и 4 | 64 ДАО'
const DESCRIPTION =
  'Метод 3 соединяет матрицу GE/McKinsey с системой 64 состояний и показывает условный переход. Метод 4 находит системное ограничение среди десяти управленческих модулей.'

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: 'https://64dao.ru/methods' },
  openGraph: { type: 'website', url: 'https://64dao.ru/methods', title: TITLE, description: DESCRIPTION },
}

function Flow({ steps }: { steps: string[] }) {
  return (
    <div className="lb-flow">
      {steps.map((s, i) => (
        <span key={s} style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          <span className="lb-flow__step">{s}</span>
          {i < steps.length - 1 && <span className="lb-flow__arrow" aria-hidden="true">→</span>}
        </span>
      ))}
    </div>
  )
}

const BTN_FONT = { fontFamily: 'inherit', fontSize: 17, fontWeight: 600 } as const

export default async function MethodsPage() {
  const year = new Date().getFullYear()
  const pricingM3 = await getPricingM3()
  const priceM3 = formatPrice(pricingM3)

  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'WebPage',
        '@id': 'https://64dao.ru/methods#webpage',
        url: 'https://64dao.ru/methods',
        name: TITLE,
        description: DESCRIPTION,
        inLanguage: 'ru-RU',
        isPartOf: { '@id': 'https://64dao.ru/#webpage' },
        publisher: { '@id': 'https://64dao.ru/#organization' },
      },
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Главная', item: 'https://64dao.ru/' },
          { '@type': 'ListItem', position: 2, name: 'Методы 3 и 4', item: 'https://64dao.ru/methods' },
        ],
      },
    ],
  }

  return (
    <div id="top" className="landing-scope lb">
      <JsonLd data={schema} />
      <LandingFonts />
      <SiteNav />

      <main>
        <section className="lb-mhero">
          <div className="lb-wrap">
            <nav className="lb-crumbs" aria-label="Хлебные крошки">
              <Link href="/">Главная</Link> <span aria-hidden="true">/</span> Методы 3 и 4
            </nav>
            <span className="lb-chip" style={{ display: 'inline-block', marginTop: 28 }}>Следующий уровень</span>
            <h1>Матрица GE/McKinsey и Алмазное колесо: куда вкладывать и что мешает</h1>
            <p>Метод 3 показывает, куда вкладывать ресурс. Метод 4 показывает, что мешает это сделать. Две диагностики по одной цене.</p>
          </div>
        </section>

        {/* ── МЕТОД 3 ── */}
        <section id="power-matrix" className="lb-sec lb-sec--cream">
          <div className="lb-wrap lb-split">
            <div className="lb-prose">
              <span className="lb-eyebrow">Матрица силы · Метод 3</span>
              <h2 className="lb-h2">От классической матрицы — к управлению изменениями</h2>
              <p>Матрица GE/McKinsey показывает положение бизнеса. 64dao показывает, куда оно сдвинется — и при каких условиях.</p>
              <p>Мы соединяем количественную оценку привлекательности рынка и силы бизнеса с системой из 64 состояний. Вы видите не только где бизнес находится сегодня:</p>
              <Flow steps={['что формирует эту позицию', 'что назрело и что перегрето', 'где точка воздействия', 'какой переход имеет смысл']} />
              <p>В одном отчёте: матрица 3×3 в логике GE/McKinsey, разбор шести факторов, назревшие и перегретые линии, приоритет вложения и очередь исполнения.</p>
              <p>64dao можно использовать самостоятельно или дополнить им классический GE/McKinsey-анализ.</p>
              <div className="lb-actions">
                <a href="/login" className="lb-btn lb-btn--red">Пройти диагностику <span aria-hidden="true">→</span></a>
                <SampleReportButton method="3" className="lb-btn lb-btn--ghost-dark" style={{ ...BTN_FONT, background: 'transparent', border: '1.5px solid #1E2A44' }}>
                  Скачать пример отчёта
                </SampleReportButton>
              </div>
            </div>
            <div className="lb-figure"><PowerMatrixSvg /></div>
          </div>
        </section>

        {/* ── МЕТОД 4 ── */}
        <section id="diamond-wheel" className="lb-sec lb-sec--white">
          <div className="lb-wrap lb-split">
            <div className="lb-figure" style={{ background: 'var(--lb-bg)', boxShadow: 'none' }}><DiamondWheelSvg /></div>
            <div className="lb-prose">
              <span className="lb-eyebrow">Алмазное колесо · Метод 4</span>
              <h2 className="lb-h2">Что мешает решению сработать</h2>
              <p>Метод 3 показывает, куда вкладывать ресурс. Метод 4 показывает, что мешает это сделать.</p>
              <p>Десять управленческих модулей — от собственности и стратегии до цены и финансов. Финансовый результат стоит в этом кругу последним: он следствие решений в остальных девяти и напрямую не чинится.</p>
              <Flow steps={['колесо из 10 модулей', 'системное ограничение', 'противоречия в решениях', 'очередь действий']} />
              <p>Диагностика ищет не самый низкий балл, а узел, который держит остальные: место, где улучшение даёт наибольший эффект, и места, где оно бесполезно, пока этот узел не развязан.</p>
              <p>Отдельным блоком — противоречия: пары управленческих решений, разумных по отдельности и тянущих компанию в разные стороны вместе. Обычный ассессмент скажет «слабое место в мотивации». Метод 4 покажет, какие именно два ваших решения друг другу мешают и что из них менять первым.</p>
              <p>Метод 4 входит в стоимость Метода 3: две диагностики по одной цене.</p>
              <div className="lb-actions">
                <a href="/login" className="lb-btn lb-btn--red">Пройти диагностику <span aria-hidden="true">→</span></a>
                <SampleReportButton method="4" className="lb-btn lb-btn--ghost-dark" style={{ ...BTN_FONT, background: 'transparent', border: '1.5px solid #1E2A44' }}>
                  Скачать пример отчёта
                </SampleReportButton>
              </div>
            </div>
          </div>
        </section>

        {/* ── СРАВНЕНИЕ ПРИОРИТЕТОВ + ТАРИФ ── */}
        <section id="price-m3" className="lb-sec lb-sec--cream">
          <div className="lb-wrap lb-split" style={{ alignItems: 'start' }}>
            <div className="lb-prose">
              <span className="lb-eyebrow">Стоимость · Метод 3</span>
              <h2 className="lb-h2">Сравнение приоритетов</h2>
              <p>Вы называете свой порядок приоритетов до диагностики. Расчёт называет свой. Отчёт показывает, на каких направлениях вы расходитесь. Это то, ради чего собирают стратегическую сессию.</p>
              <p>Отчёт говорит не о «направлении движения», а о том, куда позиция сдвинется и при каких условиях — это условный переход, а не прогноз траектории. И не о том, «что меняется», а о том, что назрело и что перегрето: назревшие и перегретые линии названы поимённо.</p>
            </div>
            <div className="lb-price lb-price--dark">
              <span className="lb-price__kicker">Оплата диагностики</span>
              <h3>{pricingM3.title}</h3>
              <div className="lb-price__amount"><b>{priceM3} {pricingM3.currency}</b><span>{pricingM3.description}</span></div>
              <div className="lb-price__rows">
                {pricingM3.features.map((row) => (
                  <div key={row.label} className="lb-price__row"><span>{row.label}</span><span>{row.value}</span></div>
                ))}
              </div>
              <a href="/login?next=/m3" className="lb-btn lb-btn--red lb-btn--block">Перейти к оплате <span aria-hidden="true">→</span></a>
              <p className="lb-price__foot" style={{ color: 'var(--lb-dim)' }}>Оплата оформляется в личном кабинете: заказ привязывается к вашей учётной записи.</p>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter year={year} />
      <CookieBanner />
    </div>
  )
}
