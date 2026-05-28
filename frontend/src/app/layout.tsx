import './globals.css'
import { ImpersonationBanner } from '@/components/ImpersonationBanner'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>
        {children}
        <ImpersonationBanner />
      </body>
    </html>
  )
}