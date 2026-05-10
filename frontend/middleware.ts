import { NextRequest, NextResponse } from 'next/server'

const PROTECTED = ['/dashboard', '/admin']
const AUTH_ONLY = ['/login', '/register', '/verify']

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl
  const hasToken = req.cookies.has('auth-token')

  if (AUTH_ONLY.some(r => pathname.startsWith(r)) && hasToken) {
    return NextResponse.redirect(new URL('/dashboard', req.url))
  }

  if (PROTECTED.some(r => pathname.startsWith(r)) && !hasToken) {
    const url = new URL('/login', req.url)
    url.searchParams.set('from', pathname)
    return NextResponse.redirect(url)
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*', '/admin/:path*', '/login', '/register', '/verify'],
}
