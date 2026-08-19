"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { API_URL, formatPrice } from "@/lib/api";

type AdminProduct = {
  id: string;
  slug: string;
  title: string;
  brand: string | null;
  price: string | null;
  is_hot: boolean;
  is_published: boolean;
  is_manual: boolean;
};

export default function AdminCatalogPage() {
  const [products, setProducts] = useState<AdminProduct[]>([]);
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [price, setPrice] = useState("");
  const [brand, setBrand] = useState("");
  const [busy, setBusy] = useState(false);

  async function load(query?: string) {
    const sp = new URLSearchParams();
    if (query) sp.set("q", query);
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/products?${sp}`, { cache: "no-store" });
      if (!res.ok) throw new Error("fail");
      setProducts(await res.json());
      setError(null);
    } catch {
      setError("Не удалось загрузить каталог");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function patch(id: string, body: Record<string, unknown>) {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/products/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(typeof data.detail === "string" ? data.detail : "Ошибка обновления");
        return;
      }
      const updated = await res.json();
      setProducts((prev) => prev.map((p) => (p.id === id ? { ...p, ...updated } : p)));
    } catch {
      setError("Сеть недоступна");
    } finally {
      setBusy(false);
    }
  }

  async function createManual(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/products`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          price: Number(price),
          brand: brand || null,
          is_hot: false,
          is_published: true,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(typeof data.detail === "string" ? data.detail : "Не удалось создать");
        return;
      }
      setTitle("");
      setPrice("");
      setBrand("");
      await load(q);
    } catch {
      setError("Сеть недоступна");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="section">
      <h2>Каталог</h2>
      <p className="lead">HOT, публикация, ручные товары и лог цен поставщиков.</p>

      <form
        className="admin-search"
        onSubmit={(e) => {
          e.preventDefault();
          void load(q);
        }}
      >
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Поиск…" />
        <button type="submit" className="btn btn-ghost admin-btn">
          Найти
        </button>
      </form>

      <form className="checkout-form admin-manual" onSubmit={createManual}>
        <h3>Ручной товар</h3>
        <label>
          Название
          <input value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>
        <label>
          Цена витрины (₽)
          <input value={price} onChange={(e) => setPrice(e.target.value)} required type="number" min={1} />
        </label>
        <label>
          Бренд
          <input value={brand} onChange={(e) => setBrand(e.target.value)} />
        </label>
        <button type="submit" className="btn btn-primary" disabled={busy}>
          Добавить
        </button>
      </form>

      {error ? <p className="form-error">{error}</p> : null}

      <table className="admin-table">
        <thead>
          <tr>
            <th>Товар</th>
            <th>Цена</th>
            <th>Флаги</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {products.map((p) => (
            <tr key={p.id}>
              <td>
                {p.title}
                <br />
                <span style={{ color: "var(--mute)" }}>
                  {p.brand ?? "—"} {p.is_manual ? "· ручной" : ""}
                </span>
              </td>
              <td>{formatPrice(p.price)}</td>
              <td>
                {p.is_hot ? "HOT " : ""}
                {p.is_published ? "витрина" : "скрыт"}
              </td>
              <td>
                <div className="admin-actions">
                  <button
                    type="button"
                    className="btn btn-ghost admin-btn"
                    disabled={busy}
                    onClick={() => patch(p.id, { is_hot: !p.is_hot })}
                  >
                    {p.is_hot ? "Снять HOT" : "HOT"}
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost admin-btn"
                    disabled={busy}
                    onClick={() => patch(p.id, { is_published: !p.is_published })}
                  >
                    {p.is_published ? "Скрыть" : "Публиковать"}
                  </button>
                  <Link href={`/admin/catalog/${p.id}`} className="btn btn-ghost admin-btn">
                    Лог цен
                  </Link>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
