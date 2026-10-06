/** @type {import('next').NextConfig} */
const nextConfig = {
  compress: true,

  // Оптимизатор изображений выключен: next/image в проекте не используется,
  // а /_next/image в Next 14 несёт критические уязвимости (аудит 2026-10-06, R001).
  // При unoptimized: true Next отвечает на /_next/image кодом 404.
  images: {
    unoptimized: true,
  },

  // CORS не нужен: Next.js — только SSR/SPA,
  // все API-запросы идут на FastAPI через браузер (credentials: include)
}

module.exports = nextConfig
