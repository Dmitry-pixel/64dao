/** @type {import('next').NextConfig} */
const nextConfig = {
  compress: true,

  images: {
    remotePatterns: [
      // Изображения стратегий раздаёт Nginx с VPS напрямую
      { protocol: 'https', hostname: '64dao.ru' },
      { protocol: 'http',  hostname: 'localhost' },
    ],
  },

  // CORS не нужен: Next.js — только SSR/SPA,
  // все API-запросы идут на FastAPI через браузер (credentials: include)
}

module.exports = nextConfig
