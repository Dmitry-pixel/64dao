import type { MetadataRoute } from 'next'
import { METHOD_ARTICLES, METHOD_LAST_UPDATED } from '@/lib/methodArticles'

/**
 * Карта сайта. Полная замена frontend/src/app/sitemap.ts.
 *
 * Статьи раздела /method датируются собственным dateModified, а не now():
 * фальшивая свежесть на статике только вредит — краулер сверяет заявленную
 * дату с содержимым.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const staticRoutes = ['', '/about']
  const documentSlugs = ['privacy-policy', 'user-agreement', 'personal-data-consent']

  const now = new Date()
  const methodUpdated = new Date(METHOD_LAST_UPDATED)

  return [
    ...staticRoutes.map((path) => ({
      url: `https://64dao.ru${path}`,
      lastModified: now,
      changeFrequency: 'weekly' as const,
      priority: path === '' ? 1 : 0.8,
    })),
    {
      url: 'https://64dao.ru/method',
      lastModified: methodUpdated,
      changeFrequency: 'monthly' as const,
      priority: 0.8,
    },
    ...METHOD_ARTICLES.map((a) => ({
      url: `https://64dao.ru/method/${a.slug}`,
      lastModified: new Date(a.dateModified),
      changeFrequency: 'monthly' as const,
      priority: 0.7,
    })),
    ...documentSlugs.map((slug) => ({
      url: `https://64dao.ru/documents/${slug}`,
      lastModified: now,
      changeFrequency: 'monthly' as const,
      priority: 0.5,
    })),
  ]
}
