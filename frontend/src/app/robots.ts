import type { MetadataRoute } from 'next'

const PRIVATE_PATHS = ['/admin', '/api', '/dashboard', '/profile', '/purchases']

// ИИ-агенты, которые обращаются к сайту по запросу пользователя
// и отдают ссылку на источник в ответе → разрешены.
const CITING_AGENTS = [
  'ChatGPT-User',
  'OAI-SearchBot',
  'Perplexity-User',
  'Claude-User',
  'Claude-SearchBot',
  'Google-Extended',
]

// Краулеры, собирающие корпус для обучения моделей
// без атрибуции источника → запрещены.
const TRAINING_CRAWLERS = [
  'GPTBot',
  'ClaudeBot',
  'Claude-Web',
  'anthropic-ai',
  'PerplexityBot',
  'CCBot',
  'Bytespider',
  'Meta-ExternalAgent',
  'Applebot-Extended',
  'Amazonbot',
  'Diffbot',
  'Omgilibot',
  'Timpibot',
]

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: '*', allow: '/', disallow: PRIVATE_PATHS },
      ...CITING_AGENTS.map((userAgent) => ({
        userAgent,
        allow: '/',
        disallow: PRIVATE_PATHS,
      })),
      { userAgent: 'YandexAdditional', allow: '/', disallow: ['/admin', '/api'] },
      ...TRAINING_CRAWLERS.map((userAgent) => ({
        userAgent,
        disallow: '/',
      })),
    ],
    sitemap: 'https://64dao.ru/sitemap.xml',
  }
}
