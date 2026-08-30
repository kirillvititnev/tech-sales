/** Same-origin admin calls: browser sends HTTP Basic after the /admin prompt. */
export function adminFetch(path: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  const isForm = typeof FormData !== "undefined" && init?.body instanceof FormData;
  if (init?.body && !isForm && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  return fetch(path, {
    cache: "no-store",
    ...init,
    credentials: "include",
    headers,
  });
}
