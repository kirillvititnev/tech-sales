const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

export type Category = {
  id: string;
  slug: string;
  name: string;
  parent_id: string | null;
  sort_order: number;
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
  admin_status: string;
  delivery_type: string;
  delivery_address?: string | null;
  comment?: string | null;
  total_amount: string;
  items?: OrderItem[];
};

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
  products: (params?: { hot?: boolean; q?: string }) => {
    const sp = new URLSearchParams();
    if (params?.hot) sp.set("hot", "true");
    if (params?.q) sp.set("q", params.q);
    const qs = sp.toString();
    return apiGet<Product[]>(`/api/v1/catalog/products${qs ? `?${qs}` : ""}`);
  },
  product: (slug: string) => apiGet<Product>(`/api/v1/catalog/products/${slug}`),
  categories: () => apiGet<Category[]>("/api/v1/catalog/categories"),
  orderByNumber: (number: string) =>
    apiGet<Order>(`/api/v1/orders/by-number/${encodeURIComponent(number)}`, {
      next: { revalidate: 0 },
      cache: "no-store",
    }),
  adminOrders: () =>
    apiGet<Order[]>("/api/v1/admin/orders", { next: { revalidate: 0 }, cache: "no-store" }),
  health: () => apiGet<{ status: string }>("/health"),
};

export { API_URL };
