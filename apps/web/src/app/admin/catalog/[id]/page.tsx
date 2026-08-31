"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useId, useState } from "react";

import { API_URL, formatPrice, productImageSrc } from "@/lib/api";
import { adminFetch } from "@/lib/adminFetch";

type AdminProduct = {
  id: string;
  title: string;
  brand: string | null;
  price: string | null;
  cost_median: string | null;
  markup_percent: string | null;
  image_url: string | null;
  is_hot: boolean;
  is_published: boolean;
  is_manual: boolean;
  price_receipt: {
    accepted_n: number;
    quarantined_n: number;
    accepted?: string[];
    quarantined: string[];
    markup_percent?: number | null;
    round_to?: number | null;
  } | null;
};

type Offer = {
  id: string;
  raw_title: string;
  raw_price: string;
  parsed_at: string;
  source_message_id: string | null;
  is_active: boolean;
  channel_title: string;
  folder_label: string | null;
};

function apiDetail(data: unknown, fallback: string): string {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

export default function AdminProductPage() {
  const params = useParams<{ id: string }>();
  const fileId = useId();
  const [product, setProduct] = useState<AdminProduct | null>(null);
  const [offers, setOffers] = useState<Offer[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!params?.id) return;
    (async () => {
      try {
        const [productRes, offerRes] = await Promise.all([
          adminFetch(`${API_URL}/api/v1/admin/products/${params.id}`),
          adminFetch(`${API_URL}/api/v1/admin/products/${params.id}/offers`),
        ]);
        if (!productRes.ok) throw new Error("fail");
        setProduct(await productRes.json());
        if (offerRes.ok) setOffers(await offerRes.json());
        setError(null);
      } catch {
        setError("Не удалось загрузить карточку");
      }
    })();
  }, [params?.id]);

  async function onUpload(file: File | undefined) {
    if (!file || !params?.id) return;
    setBusy(true);
    try {
      const body = new FormData();
      body.append("file", file);
      const res = await adminFetch(`${API_URL}/api/v1/admin/products/${params.id}/image`, {
        method: "POST",
        body,
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(apiDetail(data, "Не удалось загрузить фото"));
        return;
      }
      setProduct(await res.json());
      setError(null);
    } catch {
      setError("Сеть недоступна");
    } finally {
      setBusy(false);
    }
  }

  async function onDeletePhoto() {
    if (!params?.id) return;
    if (!window.confirm("Удалить фото с витрины?")) return;
    setBusy(true);
    try {
      const res = await adminFetch(`${API_URL}/api/v1/admin/products/${params.id}/image`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(apiDetail(data, "Не удалось удалить фото"));
        return;
      }
      setProduct(await res.json());
      setError(null);
    } catch {
      setError("Сеть недоступна");
    } finally {
      setBusy(false);
    }
  }

  const src = productImageSrc(product?.image_url ?? null);

  return (
    <main className="section">
      <p className="product-brand">
        <Link href="/admin/catalog">← Каталог</Link>
      </p>
      <h2>{product?.title ?? "Карточка"}</h2>
      <p className="lead">
        {product
          ? `${product.brand ?? "—"} · ${formatPrice(product.price)} · ${product.is_published ? "на витрине" : "скрыт"}`
          : "Фото и лог цен поставщиков."}
      </p>
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      <div className="account-group">
        <h3>Фото</h3>
        {src ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img className="admin-photo" src={src} alt={product?.title ?? ""} />
        ) : (
          <p className="account-note">Пока нет фото. JPEG, PNG или WebP, до 2 МБ.</p>
        )}
        <div className="admin-actions">
          <label className="btn btn-ghost admin-btn" htmlFor={fileId}>
            {src ? "Заменить фото" : "Загрузить фото"}
          </label>
          <input
            id={fileId}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            hidden
            disabled={busy}
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              void onUpload(file);
            }}
          />
          {src ? (
            <button type="button" className="btn btn-ghost admin-btn" disabled={busy} onClick={() => void onDeletePhoto()}>
              Удалить фото
            </button>
          ) : null}
        </div>
      </div>

      <div className="account-group">
        <h3>Цена витрины</h3>
        {product ? (
          <>
            <p className="account-note">
              медиана поставщиков {formatPrice(product.cost_median)} · наценка{" "}
              {product.markup_percent ?? "0"}% · витрина {formatPrice(product.price)}
            </p>
            {product.price_receipt ? (
              <>
                <p className="account-note">
                  в медиане {product.price_receipt.accepted_n}
                  {product.price_receipt.quarantined_n
                    ? ` · отброшено ${product.price_receipt.quarantined_n}`
                    : ""}
                </p>
                {(product.price_receipt.accepted?.length ?? 0) > 0 ? (
                  <ul className="account-list">
                    {product.price_receipt.accepted!.map((item) => (
                      <li key={`a-${item}`}>{item}</li>
                    ))}
                  </ul>
                ) : null}
                {product.price_receipt.quarantined.length > 0 ? (
                  <ul className="account-list">
                    {product.price_receipt.quarantined.map((item) => (
                      <li key={`q-${item}`}>{item}</li>
                    ))}
                  </ul>
                ) : null}
              </>
            ) : (
              <p className="account-note">квиток медианы появится после синка</p>
            )}
          </>
        ) : (
          <p className="account-note">загрузка…</p>
        )}
      </div>

      <h3>Лог цен</h3>
      <p className="lead">Офферы поставщиков по карточке (канал, сырой title, цена, время).</p>
      <table className="admin-table">
        <thead>
          <tr>
            <th>Канал</th>
            <th>Сырой title</th>
            <th>Цена</th>
            <th>Когда</th>
            <th>Msg</th>
            <th>Активен</th>
          </tr>
        </thead>
        <tbody>
          {offers.length === 0 ? (
            <tr>
              <td colSpan={6}>Офферов нет (ручной товар или ещё не сматчен)</td>
            </tr>
          ) : (
            offers.map((o) => (
              <tr key={o.id}>
                <td>
                  {o.channel_title}
                  <br />
                  <span className="account-note">{o.folder_label ?? ""}</span>
                </td>
                <td>{o.raw_title}</td>
                <td>{formatPrice(o.raw_price)}</td>
                <td>{new Date(o.parsed_at).toLocaleString("ru-RU")}</td>
                <td>{o.source_message_id ?? "—"}</td>
                <td>{o.is_active ? "да" : "нет"}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </main>
  );
}
