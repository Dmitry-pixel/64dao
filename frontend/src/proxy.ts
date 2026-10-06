import { NextResponse, NextRequest } from "next/server";

// Режим обслуживания: при включённом режиме страницы сайта подменяются на
// /maintenance. Маршруты не охраняет — авторизация только на backend.
//
// Файл обязан лежать в src/ рядом с src/app. До 2026-10-06 он лежал в корне
// frontend/ как middleware.ts, Next его не подхватывал, и режим не работал.

const BYPASS_PREFIXES = [
  "/admin",
  "/login",
  "/verify",
  "/maintenance",
  "/api",
  "/_next",
  "/favicon.ico",
  "/robots.txt",
  "/sitemap.xml",
];

// Напрямую в контейнер backend по сети Docker, минуя nginx и публичный адрес.
const SITE_MODE_URL =
  process.env.SITE_MODE_URL || "http://backend:8000/api/site-mode";

// Ответ кэшируется в памяти процесса, чтобы не спрашивать backend на каждой
// странице. Включение и выключение режима доходит до сайта за это время.
const CACHE_MS = 10_000;

let cached = { enabled: false, at: 0 };
let inflight: Promise<boolean> | null = null;

function isBypassed(pathname: string): boolean {
  // Файлы из public/ (картинки, шрифты) нужны и самой странице обслуживания.
  if (/\.[a-z0-9]+$/i.test(pathname)) return true;
  return BYPASS_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(p + "/")
  );
}

async function fetchMode(): Promise<boolean> {
  try {
    const res = await fetch(SITE_MODE_URL, {
      cache: "no-store",
      signal: AbortSignal.timeout(2000),
    });
    if (res.ok) {
      const data = await res.json();
      return Boolean(data.enabled);
    }
  } catch {
    // backend недоступен — остаёмся в последнем известном состоянии
  }
  return cached.enabled;
}

async function isMaintenance(): Promise<boolean> {
  if (Date.now() - cached.at < CACHE_MS) return cached.enabled;
  if (!inflight) {
    inflight = fetchMode().then((enabled) => {
      cached = { enabled, at: Date.now() };
      inflight = null;
      return enabled;
    });
  }
  return inflight;
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (isBypassed(pathname) || !(await isMaintenance())) {
    return NextResponse.next();
  }
  const url = request.nextUrl.clone();
  url.pathname = "/maintenance";
  return NextResponse.rewrite(url);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image).*)"],
};
