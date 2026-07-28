import type { MetadataRoute } from 'next'

const PRIVATE_PATHS = ['/admin', '/api', '/dashboard', '/profile', '/purchases']

// Публичные исключения из PRIVATE_PATHS.
// Более длинный Allow имеет приоритет над более коротким Disallow.
const PUBLIC_PATHS = ['/', '/api/sample-report']

// ИИ-агенты, которые обращаются к сайту по запросу пользователя
// и отдают ссылку на источник в ответе → разрешены.
const CITING_AGENTS = [
  'ChatGPT-User',
  'OAI-SearchBot',
  'Perplexity-User',
  'Claude-User',
  'Claude-SearchBot',
]

// Google-Extended — не краулер, а управляющий токен. Регулирует
// использование контента в Gemini, Vertex AI и AI Overviews.
// Атрибуцию не гарантирует. Разрешён сознательно: блокировка
// убирает сайт из AI Overviews, цена — обучение Gemini.
const GOOGLE_AI = 'Google-Extended'

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
      { userAgent: '*', allow: PUBLIC_PATHS, disallow: PRIVATE_PATHS },
      ...CITING_AGENTS.map((userAgent) => ({
        userAgent,
        allow: PUBLIC_PATHS,
        disallow: PRIVATE_PATHS,
      })),
      { userAgent: GOOGLE_AI, allow: PUBLIC_PATHS, disallow: PRIVATE_PATHS },
      {
        userAgent: 'YandexAdditional',
        allow: PUBLIC_PATHS,
        disallow: ['/admin', '/api'],
      },
      ...TRAINING_CRAWLERS.map((userAgent) => ({
        userAgent,
        disallow: '/',
      })),
    ],
    sitemap: 'https://64dao.ru/sitemap.xml',
  }
}
