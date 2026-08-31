const PREFIX = "whiteshop.orderAccess.";

function storageKey(number: string): string {
  return PREFIX + number.trim().toUpperCase();
}

export function stashOrderAccess(number: string, access: string): void {
  if (!access || typeof window === "undefined") return;
  try {
    sessionStorage.setItem(storageKey(number), access);
  } catch {
    // Private mode can block sessionStorage.
  }
}

export function readOrderAccess(number: string): string {
  if (typeof window === "undefined" || !number) return "";
  const key = storageKey(number);
  let stored = "";
  try {
    stored = sessionStorage.getItem(key) ?? "";
  } catch {
    stored = "";
  }
  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("access") ?? "";
  let fromHash = "";
  if (window.location.hash.startsWith("#access=")) {
    fromHash = decodeURIComponent(window.location.hash.slice("#access=".length));
  }
  const access = fromQuery || fromHash || stored;
  if (access && access !== stored) {
    try {
      sessionStorage.setItem(key, access);
    } catch {
      // ignore
    }
  }
  if (fromQuery || fromHash) {
    const url = new URL(window.location.href);
    url.searchParams.delete("access");
    url.hash = "";
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}`);
  }
  return access;
}
