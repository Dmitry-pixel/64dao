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
  return raw
}

/** Адрес входа с возвратом на текущую страницу (включая #якорь). */
export function loginUrlHere(): string {
  if (typeof window === 'undefined') return '/login'
  const here = window.location.pathname + window.location.search + window.location.hash
  return `/login?next=${encodeURIComponent(here)}`
}
