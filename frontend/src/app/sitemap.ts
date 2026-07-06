import type { MetadataRoute } from 'next'

export default function sitemap(): MetadataRoute.Sitemap {
  const staticRoutes = ['', '/about']
  const documentSlugs = ['privacy-policy', 'user-agreement', 'personal-data-consent']

  const now = new Date()

  return [
    ...staticRoutes.map((path) => ({
      url: `https://64dao.ru${path}`,
      lastModified: now,
      changeFrequency: 'weekly' as const,
      priority: path === '' ? 1 : 0.8,
    })),
    ...documentSlugs.map((slug) => ({
      url: `https://64dao.ru/documents/${slug}`,
      lastModified: now,
      changeFrequency: 'monthly' as const,
      priority: 0.5,
    })),
  ]
}
