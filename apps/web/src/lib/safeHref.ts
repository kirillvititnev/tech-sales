const PATH_PREFIXES = [
  "/account",
  "/catalog",
  "/cart",
  "/checkout",
  "/hot",
  "/login",
  "/register",
  "/privacy",
  "/order",
  "/product",
  "/mini",
];

export function safeNextHref(raw: string | null | undefined, fallback: string): string {
  if (!raw) return fallback;
  let value = raw.trim();
  try {
    value = decodeURIComponent(value);
  } catch {
    return fallback;
  }
  if (!value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return fallback;
  if (value.includes("\\") || value.includes("://") || value.includes("@")) return fallback;
  try {
    const parsed = new URL(value, "https://whiteshop.local");
    if (parsed.origin !== "https://whiteshop.local") return fallback;
    if (parsed.username || parsed.password) return fallback;
    const path = parsed.pathname;
    const allowed =
      path === "/" || PATH_PREFIXES.some((prefix) => path === prefix || path.startsWith(`${prefix}/`));
    if (!allowed) return fallback;
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return fallback;
  }
}
