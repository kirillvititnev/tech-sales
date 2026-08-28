function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i++) out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return out === 0;
}

function unauthorized(): Response {
  return new Response("Требуется вход в админку", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="White Shop admin"',
      "Cache-Control": "no-store",
    },
  });
}

export function proxy(request: Request): Response | undefined {
  const user = process.env.ADMIN_USERNAME ?? "";
  const password = process.env.ADMIN_PASSWORD ?? "";
  if (!user || !password) {
    return new Response("Админка не сконфигурирована", { status: 503 });
  }

  const header = request.headers.get("authorization") ?? "";
  if (!header.startsWith("Basic ")) {
    return unauthorized();
  }
  let decoded = "";
  try {
    decoded = atob(header.slice(6).trim());
  } catch {
    return unauthorized();
  }
  const sep = decoded.indexOf(":");
  const gotUser = sep >= 0 ? decoded.slice(0, sep) : decoded;
  const gotPass = sep >= 0 ? decoded.slice(sep + 1) : "";
  if (!safeEqual(gotUser, user) || !safeEqual(gotPass, password)) {
    return unauthorized();
  }
  return undefined;
}

export const config = {
  matcher: ["/admin", "/admin/:path*", "/api/v1/admin", "/api/v1/admin/:path*"],
};
