import { buildFaqData } from '@/lib/faqData'

const FAQ_CSS = `
.faq-list { margin-top: 48px; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); }
.faq-item > summary { list-style: none; cursor: pointer; padding: 24px 0 24px; border-top: 1px solid var(--border); display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; }
.faq-item > summary::-webkit-details-marker { display: none; }
.faq-item > summary::marker { content: ''; }
.faq-item > summary h3 { margin: 0; font-family: inherit; font-size: 18px; font-weight: 500; line-height: 1.4; color: var(--foreground); }
.faq-sign { margin-top: 4px; font-size: 24px; line-height: 1; color: var(--accent); flex-shrink: 0; }
.faq-sign::after { content: '+'; }
.faq-item[open] .faq-sign::after { content: '\\2013'; }
.faq-answer { margin: -8px 0 24px; max-width: 780px; font-size: 14px; line-height: 1.6; color: var(--muted-foreground); }
`

export default function FaqSection({ priceLabel }: { priceLabel: string }) {
  const FAQ_DATA = buildFaqData(priceLabel)
  return (
    <section
      id="faq"
      style={{
        borderBottom: '1px solid rgba(0,0,0,0.06)',
        background: 'color-mix(in oklab, var(--muted) 40%, var(--background))',
      }}
    >
      <style dangerouslySetInnerHTML={{ __html: FAQ_CSS }} />
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '96px 40px' }}>
        <div
          style={{
            marginBottom: 16,
            fontSize: 12,
            textTransform: 'uppercase',
            letterSpacing: '0.22em',
            color: 'var(--muted-foreground)',
          }}
        >
          Честные ответы
        </div>
        <h2
          style={{
            margin: 0,
            fontFamily: "'Golos Text',sans-serif",
            fontSize: 'clamp(32px,4.6vw,48px)',
            lineHeight: 1.1,
            color: 'var(--foreground)',
          }}
        >
          Что обычно спрашивают о 64 ДАО
        </h2>
        <div className="faq-list">
          {FAQ_DATA.map((item, i) => (
            <details key={i} className="faq-item">
              <summary>
                <h3>{item.q}</h3>
                <span className="faq-sign" aria-hidden="true" />
              </summary>
              <p className="faq-answer">{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  )
}
