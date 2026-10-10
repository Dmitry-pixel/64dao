'use client'
/**
 * Постраничный вывод длинных списков: «Мои отчёты», «Мои компании»,
 * «Пользователи», кабинет пользователя.
 *
 * Листание идёт на клиенте: списки отчётов собираются из трёх источников
 * (Методы 1–2, 3 и 4) и сортируются по дате уже в браузере, поэтому
 * серверная пагинация потребовала бы общего эндпоинта. При текущих объёмах
 * (сотни строк) это не нужно. Если список дорастёт до тысяч строк,
 * переводить на limit/offset на сервере, а этот компонент оставить как есть.
 */
import { useMemo, useState } from 'react'

export function usePaged<T>(items: T[], pageSize: number, resetKey: unknown = null) {
  // Страница хранится вместе с ключом сброса (поиск, фильтр). Сменился
  // ключ: считаем, что открыта первая страница. Без эффекта и лишнего рендера.
  const [state, setState] = useState<{ key: unknown; page: number }>({ key: resetKey, page: 0 })
  const page = Object.is(state.key, resetKey) ? state.page : 0
  const setPage = (p: number) => setState({ key: resetKey, page: p })
  const pages = Math.max(1, Math.ceil(items.length / pageSize))

  // После удаления строки последняя страница может опустеть: прижимаем.
  const current = Math.min(page, pages - 1)
  const offset = current * pageSize
  const pageItems = useMemo(() => items.slice(offset, offset + pageSize), [items, offset, pageSize])
  return { page: current, setPage, pages, offset, pageItems, total: items.length }
}

/** Номера страниц: первая, последняя и соседние с текущей, между ними «…». */
function pageList(page: number, pages: number): (number | '…')[] {
  const keep = new Set([0, pages - 1, page - 1, page, page + 1])
  const out: (number | '…')[] = []
  for (let i = 0; i < pages; i++) {
    if (!keep.has(i)) continue
    const prev = out[out.length - 1]
    if (typeof prev === 'number' && i - prev > 1) out.push('…')
    out.push(i)
  }
  return out
}

export function Pager({
  page, pages, offset, shown, total, onPage, anchorId,
}: {
  page: number
  pages: number
  offset: number
  shown: number
  total: number
  onPage: (p: number) => void
  /** id элемента, к началу которого прокрутить после смены страницы. */
  anchorId?: string
}) {
  if (pages <= 1) return null

  const go = (p: number) => {
    onPage(p)
    if (anchorId) document.getElementById(anchorId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  const btn = { padding: '6px 12px', fontSize: 12, minWidth: 34 }

  return (
    <nav className="pager" aria-label="Страницы списка">
      <span className="pager-info">
        {offset + 1}–{offset + shown} из {total}
      </span>
      <span className="pager-buttons">
        <button type="button" className="btn btn-ghost" style={btn}
          disabled={page === 0} onClick={() => go(page - 1)}>← Назад</button>
        {pageList(page, pages).map((p, i) => p === '…'
          ? <span key={`gap-${i}`} className="pager-gap">…</span>
          : (
            <button key={p} type="button" className="btn btn-ghost"
              aria-current={p === page ? 'page' : undefined}
              style={{
                ...btn,
                background: p === page ? '#1a2540' : undefined,
                color: p === page ? '#fff' : undefined,
                borderColor: p === page ? '#1a2540' : undefined,
              }}
              onClick={() => go(p)}>{p + 1}</button>
          ))}
        <button type="button" className="btn btn-ghost" style={btn}
          disabled={page >= pages - 1} onClick={() => go(page + 1)}>Вперёд →</button>
      </span>
    </nav>
  )
}
