/** Browser uses same origin (Next proxies `/api` → FastAPI). Server talks to FastAPI directly. */
export function resolveApiUrl(options: {
  isBrowser: boolean;
  publicUrl?: string | null;
  internalUrl?: string | null;
}): string {
  const internal = (options.internalUrl || "http://127.0.0.1:8000").replace(/\/$/, "");
  if (!options.isBrowser) return internal;
  const pub = (options.publicUrl ?? "").trim();
  if (!pub || pub === "same-origin") return "";
  return pub.replace(/\/$/, "");
}

const API_URL = resolveApiUrl({
  isBrowser: typeof window !== "undefined",
  publicUrl: process.env.NEXT_PUBLIC_API_URL,
  internalUrl: process.env.API_INTERNAL_URL,
});

export type Product = {
  id: string;
  slug: string;
  title: string;
  brand: string | null;
  price: string | null;
  is_hot: boolean;
  image_url: string | null;
  attributes?: Record<string, unknown>;
  description?: string | null;
};

const MEDIA_PREFIX = "/api/v1/catalog/media/";

export function productImageSrc(url: string | null | undefined): string | null {
  if (!url || !url.startsWith(MEDIA_PREFIX)) return null;
  const name = url.slice(MEDIA_PREFIX.length);
  if (!/^[0-9a-f]{32}\.(jpg|png|webp)$/.test(name)) return null;
  // Always same-origin so SSR and the browser match (Next rewrites `/api` → FastAPI).
  return url;
}

export type Category = {
  id: string;
  slug: string;
  name: string;
  parent_id: string | null;
  sort_order: number;
};

export type SuggestItem = {
  slug: string;
  title: string;
  brand: string | null;
  price: string | null;
  device_category: string | null;
  device_name: string | null;
};

export type FacetValue = {
  value: string;
  count: number;
};

export type CatalogFacets = {
  brands: FacetValue[];
  device_categories: FacetValue[];
  price_min: string | null;
  price_max: string | null;
  total: number;
};

export type CatalogSort =
  | "relevance"
  | "price_asc"
  | "price_desc"
  | "name_asc"
  | "name_desc"
  | "brand_asc"
  | "newest"
  | "hot";

export type CatalogQuery = {
  q?: string;
  brand?: string;
  category_id?: string;
  device_category?: string;
  hot?: boolean;
  min_price?: number;
  max_price?: number;
  sort?: CatalogSort;
  limit?: number;
  offset?: number;
  ids?: string[];
};

export type OrderItem = {
  id: string;
  product_id: string | null;
  title: string;
  unit_price: string;
  quantity: number;
};

export type Order = {
  id: string;
  number: string;
  customer_name: string;
  customer_phone: string;
  customer_telegram?: string | null;
  customer_status: string;
  admin_status?: string;
  delivery_type: string;
  delivery_address?: string | null;
  comment?: string | null;
  total_amount: string;
  bonus_spent?: string;
  items?: OrderItem[];
  access_token?: string | null;
};

function buildCatalogParams(params?: CatalogQuery): URLSearchParams {
  const sp = new URLSearchParams();
  if (!params) {
    sp.set("limit", "120");
    return sp;
  }
  if (params.ids?.length) {
    for (const id of params.ids.slice(0, 50)) {
      sp.append("ids", id);
    }
    return sp;
  }
  if (params.hot) sp.set("hot", "true");
  if (params.q) sp.set("q", params.q);
  if (params.brand) sp.set("brand", params.brand);
  if (params.category_id) sp.set("category_id", params.category_id);
  if (params.device_category) sp.set("device_category", params.device_category);
  if (params.min_price != null) sp.set("min_price", String(params.min_price));
  if (params.max_price != null) sp.set("max_price", String(params.max_price));
  if (params.sort) sp.set("sort", params.sort);
  sp.set("limit", String(params.limit ?? 120));
  if (params.offset) sp.set("offset", String(params.offset));
  return sp;
}

function adminAuthHeaders(): HeadersInit {
  if (typeof window !== "undefined") return {};
  const user = process.env.ADMIN_USERNAME ?? "";
  const pass = process.env.ADMIN_PASSWORD ?? "";
  if (!user || !pass) return {};
  const token = Buffer.from(`${user}:${pass}`).toString("base64");
  return { Authorization: `Basic ${token}` };
}

async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    next: { revalidate: 30 },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}

/** Client-side fetch without Next cache — for interactive catalog. */
async function apiGetLive<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}

export function apiErrorMessage(data: unknown, fallback: string): string {
  if (typeof data === "object" && data !== null && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (Array.isArray(detail) && detail[0] && typeof detail[0] === "object" && detail[0] !== null) {
      const first = detail[0] as { msg?: unknown };
      if (typeof first.msg === "string" && first.msg.trim()) return first.msg;
    }
  }
  return fallback;
}

export function formatPrice(price: string | null): string {
  if (!price) return "—";
  const n = Number(price);
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    maximumFractionDigits: 0,
  }).format(n);
}

export const api = {
  products: (params?: CatalogQuery) => {
    const qs = buildCatalogParams(params).toString();
    return apiGet<Product[]>(`/api/v1/catalog/products?${qs}`);
  },
  productsLive: (params?: CatalogQuery) => {
    const qs = buildCatalogParams(params).toString();
    return apiGetLive<Product[]>(`/api/v1/catalog/products?${qs}`);
  },
  facets: (params?: CatalogQuery) => {
    const sp = buildCatalogParams(params);
    sp.delete("limit");
    sp.delete("offset");
    sp.delete("sort");
    const qs = sp.toString();
    return apiGet<CatalogFacets>(`/api/v1/catalog/facets${qs ? `?${qs}` : ""}`);
  },
  facetsLive: (params?: CatalogQuery) => {
    const sp = buildCatalogParams(params);
    sp.delete("limit");
    sp.delete("offset");
    sp.delete("sort");
    const qs = sp.toString();
    return apiGetLive<CatalogFacets>(`/api/v1/catalog/facets${qs ? `?${qs}` : ""}`);
  },
  suggestLive: (q: string, limit = 8) => {
    const sp = new URLSearchParams({ q, limit: String(limit) });
    return apiGetLive<SuggestItem[]>(`/api/v1/catalog/suggest?${sp}`);
  },
  product: (slug: string) => apiGet<Product>(`/api/v1/catalog/products/${slug}`),
  categories: () => apiGet<Category[]>("/api/v1/catalog/categories"),
  orderByNumber: (number: string, access: string) =>
    apiGet<Order>(`/api/v1/orders/by-number/${encodeURIComponent(number)}`, {
      next: { revalidate: 0 },
      cache: "no-store",
      headers: { "X-Order-Access": access },
    }),
  adminOrders: () =>
    apiGet<Order[]>("/api/v1/admin/orders", {
      next: { revalidate: 0 },
      cache: "no-store",
      headers: adminAuthHeaders(),
    }),
  health: () => apiGet<{ status: string }>("/health"),
};

export { API_URL };
