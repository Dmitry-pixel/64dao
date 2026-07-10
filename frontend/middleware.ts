import { NextResponse, NextRequest } from "next/server";

const BYPASS_PREFIXES = [
  "/admin",
  "/login",
  "/verify",
  "/maintenance",
  "/api",
  "/favicon.ico",
  "/robots.txt",
  "/sitemap.xml",
];

function isBypassed(pathname: string): boolean {
  return BYPASS_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(p + "/")
  );
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (isBypassed(pathname)) {
    return NextResponse.next();
  }

  let enabled = false;
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const res = await fetch(`${apiUrl}/api/site-mode`, {
      cache: "no-store",
      signal: AbortSignal.timeout(2000),
    });
    if (res.ok) {
      const data = await res.json();
      enabled = Boolean(data.enabled);
    }
  } catch {
    enabled = false;
  }

  if (enabled) {
    const url = request.nextUrl.clone();
    url.pathname = "/maintenance";
    return NextResponse.rewrite(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image).*)"],
};
