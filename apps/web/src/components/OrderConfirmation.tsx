"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { API_URL, formatPrice, type Order } from "@/lib/api";

const STATUS_RU: Record<string, string> = {
  placed: "Оформлен",
  paid: "Оплачен",
  cancelled: "Отменён",
  ready: "Готов к выдаче",
  issued: "Выдан",
};

const DELIVERY_RU: Record<string, string> = {
  pickup_moscow: "Самовывоз, Москва",
  cdek: "СДЭК",
};

export function OrderConfirmation({
  catalogHref = "/#catalog",
}: {
  catalogHref?: string;
}) {
  const params = useParams<{ number: string }>();
  const searchParams = useSearchParams();
  const number = decodeURIComponent(params?.number ?? "").toUpperCase();
  const access = searchParams.get("access") ?? "";
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!number || !access) {
      setLoading(false);
      setError("not_found");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `${API_URL}/api/v1/orders/by-number/${encodeURIComponent(number)}?access=${encodeURIComponent(access)}`,
          { cache: "no-store" },
        );
        if (!res.ok) {
          throw new Error(res.status === 404 ? "not_found" : "fail");
        }
        const data = (await res.json()) as Order;
        if (!cancelled) setOrder(data);
      } catch (e) {
        if (!cancelled) {
          // Order was created (admin has it) — still show the number.
          setError(e instanceof Error && e.message === "not_found" ? "not_found" : "load_fail");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [number, access]);

  if (loading) {
    return (
      <main className="section">
        <h2>Заказ…</h2>
        <p className="lead">Загружаем подтверждение.</p>
      </main>
    );
  }

  if (!order) {
    return (
      <main className="section">
        <p className="product-brand">Заказ принят</p>
        <h2>{number || "—"}</h2>
        <p className="lead">
          {error === "not_found"
            ? "Заказ записан. Откройте ссылку из письма/экрана подтверждения — в ней есть ключ доступа."
            : "Заказ отправлен. Менеджер свяжется с вами для оплаты. Детали заказа подгрузятся при обновлении страницы."}
        </p>
        <div className="cta-row">
          <Link href={catalogHref} className="btn btn-primary">
            В каталог
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="section">
      <p className="product-brand">Заказ принят</p>
      <h2>{order.number}</h2>
      <p className="lead">
        Менеджер свяжется с вами для подтверждения и оплаты. Онлайн-оплаты нет.
      </p>
      <dl className="order-meta">
        <div>
          <dt>Статус</dt>
          <dd>{STATUS_RU[order.customer_status] ?? order.customer_status}</dd>
        </div>
        <div>
          <dt>Доставка</dt>
          <dd>{DELIVERY_RU[order.delivery_type] ?? order.delivery_type}</dd>
        </div>
        {order.delivery_address ? (
          <div>
            <dt>Адрес</dt>
            <dd>{order.delivery_address}</dd>
          </div>
        ) : null}
        <div>
          <dt>Сумма</dt>
          <dd>{formatPrice(order.total_amount)}</dd>
        </div>
        <div>
          <dt>Контакт</dt>
          <dd>
            {order.customer_name}, {order.customer_phone}
            {order.customer_telegram ? ` · ${order.customer_telegram}` : ""}
          </dd>
        </div>
      </dl>
      <ul className="order-items">
        {order.items?.map((item) => (
          <li key={item.id}>
            {item.title} × {item.quantity} — {formatPrice(String(item.unit_price))}
          </li>
        ))}
      </ul>
      <div className="cta-row">
        <Link href={catalogHref} className="btn btn-primary">
          В каталог
        </Link>
      </div>
    </main>
  );
}
