"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { API_URL, formatPrice } from "@/lib/api";

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

export default function AdminProductOffersPage() {
  const params = useParams<{ id: string }>();
  const [offers, setOffers] = useState<Offer[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params?.id) return;
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/admin/products/${params.id}/offers`, {
          cache: "no-store",
        });
        if (!res.ok) throw new Error("fail");
        setOffers(await res.json());
      } catch {
        setError("Не удалось загрузить лог цен");
      }
    })();
  }, [params?.id]);

  return (
    <main className="section">
      <p className="product-brand">
        <Link href="/admin/catalog">← Каталог</Link>
      </p>
      <h2>Лог цен</h2>
      <p className="lead">Офферы поставщиков по карточке (канал, сырой title, цена, время).</p>
      {error ? <p className="form-error">{error}</p> : null}
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
                  <span style={{ color: "var(--mute)" }}>{o.folder_label ?? ""}</span>
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
