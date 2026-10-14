/**
 * Возврат на исходную страницу после входа (?next=).
 *
 * Принимается только относительный путь сайта: «/report/…», но не
 * «//evil.ru» и не «https://…». Иначе ссылка из письма или чужого сайта
 * уводила бы пользователя после входа на постороннюю страницу.
 */
export function safeNext(raw: string | null | undefined): string | null {
  if (!raw || raw.length > 500) return null
  if (!raw.startsWith('/') || raw.startsWith('//') || raw.startsWith('/\\')) return null
  // Возврат на страницу входа или кода замкнул бы круг.
  if (/^\/(login|verify)(\/|\?|#|$)/.test(raw)) return null
  return raw
}

/** Адрес входа с возвратом на текущую страницу (включая #якорь). */
export function loginUrlHere(): string {
  if (typeof window === 'undefined') return '/login'
  // Только первый #якорь: роутер мог дописать его повторно.
  const hash = window.location.hash ? '#' + window.location.hash.slice(1).split('#')[0] : ''
  const here = window.location.pathname + window.location.search + hash
  return `/login?next=${encodeURIComponent(here)}`
}
