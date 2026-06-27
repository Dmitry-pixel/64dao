/**
 * LandingFonts — подключает Google Fonts (Golos Text, Inter) локально,
 * только на страницах лендинга. Не трогает общий app/layout.tsx, чтобы
 * не грузить эти шрифты глобально на /admin, /dashboard, /login и т.д.
 *
 * Next.js App Router поднимает теги из тела компонента страницы в <head>
 * автоматически, если они отрендерены до основного контента.
 */
export default function LandingFonts() {
  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      <link
        href="https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600;700;800;900&family=Inter:wght@400;500;600;700;800&display=swap"
        rel="stylesheet"
      />
    </>
  )
}
