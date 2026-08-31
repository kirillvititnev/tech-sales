"use client";

import Link from "next/link";
import { useCallback, useEffect, useId, useState } from "react";

import { API_URL, formatPrice, productImageSrc } from "@/lib/api";
import { adminFetch } from "@/lib/adminFetch";

type AdminProduct = {
  id: string;
  slug: string;
  title: string;
  brand: string | null;
  price: string | null;
  is_hot: boolean;
  is_published: boolean;
  is_manual: boolean;
  image_url: string | null;
};

type AdminProductList = {
  items: AdminProduct[];
  total: number;
  limit: number;
  offset: number;
};

const PAGE_SIZE = 50;

export default function AdminCatalogPage() {
  const searchId = useId();
  const [products, setProducts] = useState<AdminProduct[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [page, setPage] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [price, setPrice] = useState("");
  const [brand, setBrand] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedQ(q.trim()), 280);
    return () => window.clearTimeout(t);
  }, [q]);

  const load = useCallback(async (query: string, pageIndex: number) => {
    const sp = new URLSearchParams();
    if (query) sp.set("q", query);
    sp.set("limit", String(PAGE_SIZE));
    sp.set("offset", String(pageIndex * PAGE_SIZE));
    try {
      const res = await adminFetch(`${API_URL}/api/v1/admin/products?${sp}`);
      if (!res.ok) throw new Error("fail");
      const data = (await res.json()) as AdminProductList;
      setProducts(data.items ?? []);
      setTotal(data.total ?? 0);
      setError(null);
    } catch {
      setError("Не удалось загрузить каталог");
    }
  }, []);

  useEffect(() => {
    setPage(0);
  }, [debouncedQ]);

  useEffect(() => {
    void load(debouncedQ, page);
  }, [debouncedQ, page, load]);

  async function patch(id: string, body: Record<string, unknown>) {
    setBusy(true);
    try {
      const res = await adminFetch(`${API_URL}/api/v1/admin/products/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(typeof data.detail === "string" ? data.detail : "Ошибка обновления");
        return;
      }
      const updated = (await res.json()) as AdminProduct;
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
      const res = await adminFetch(`${API_URL}/api/v1/admin/products`, {
        method: "POST",
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
      setPage(0);
      await load(debouncedQ, 0);
    } catch {
      setError("Сеть недоступна");
    } finally {
      setBusy(false);
    }
  }

  const from = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const to = Math.min(total, (page + 1) * PAGE_SIZE);
  const lastPage = Math.max(0, Math.ceil(total / PAGE_SIZE) - 1);

  return (
    <main className="section">
      <h2>Каталог</h2>
      <p className="lead">HOT, публикация, фото, ручные товары и лог цен поставщиков.</p>

      <form
        className="admin-search"
        onSubmit={(e) => {
          e.preventDefault();
          setDebouncedQ(q.trim());
          setPage(0);
        }}
      >
        <label htmlFor={searchId}>Поиск</label>
        <input
          id={searchId}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Название, бренд или slug"
          autoComplete="off"
        />
        <button type="submit" className="btn btn-ghost admin-btn">
          Найти
        </button>
      </form>

      <p className="account-note">
        {total === 0 ? "Ничего не найдено." : `Показаны ${from}–${to} из ${total}`}
      </p>

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

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      <table className="admin-table">
        <thead>
          <tr>
            <th>Фото</th>
            <th>Товар</th>
            <th>Цена</th>
            <th>Флаги</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {products.map((p) => {
            const src = productImageSrc(p.image_url);
            return (
              <tr key={p.id}>
                <td>
                  {src ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img className="admin-thumb" src={src} alt="" />
                  ) : (
                    <span className="admin-thumb is-empty" aria-hidden="true" />
                  )}
                </td>
                <td>
                  {p.title}
                  <br />
                  <span className="account-note">
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
                      Карточка
                    </Link>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="admin-pager">
        <button
          type="button"
          className="btn btn-ghost admin-btn"
          disabled={page <= 0}
          onClick={() => setPage((p) => Math.max(0, p - 1))}
        >
          Назад
        </button>
        <span className="account-note">
          Страница {page + 1} из {lastPage + 1}
        </span>
        <button
          type="button"
          className="btn btn-ghost admin-btn"
          disabled={page >= lastPage}
          onClick={() => setPage((p) => p + 1)}
        >
          Дальше
        </button>
      </div>
    </main>
  );
}
