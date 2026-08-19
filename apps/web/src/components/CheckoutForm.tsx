"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { formatPrice, type Product } from "@/lib/api";
import type { CheckoutPrefill } from "@/lib/telegramUser";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type DeliveryType = "pickup_moscow" | "cdek";

export function CheckoutForm({
  product,
  defaults,
  successHref,
}: {
  product: Product;
  defaults?: CheckoutPrefill;
  successHref?: (number: string) => string;
}) {
  const router = useRouter();
  const [name, setName] = useState(defaults?.name ?? "");
  const [phone, setPhone] = useState("");
  const [telegram, setTelegram] = useState(defaults?.telegram ?? "");
  const [delivery, setDelivery] = useState<DeliveryType>("pickup_moscow");
  const [address, setAddress] = useState("");
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (defaults?.name) setName(defaults.name);
    if (defaults?.telegram) setTelegram(defaults.telegram);
  }, [defaults?.name, defaults?.telegram]);

  const needsAddress = delivery === "cdek";
  const priceLabel = useMemo(() => formatPrice(product.price), [product.price]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/orders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer_name: name,
          customer_phone: phone,
          customer_telegram: telegram || null,
          delivery_type: delivery,
          delivery_address: needsAddress ? address : null,
          comment: comment || null,
          items: [{ product_id: product.id, quantity: 1 }],
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Не удалось оформить заказ");
        return;
      }
      const href = successHref ? successHref(data.number) : `/order/${data.number}`;
      router.push(href);
    } catch {
      setError("Сеть недоступна. Проверьте API.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="checkout-form" onSubmit={onSubmit}>
      <div className="checkout-summary">
        <p className="product-brand">{product.brand ?? "Техника"}</p>
        <h3>{product.title}</h3>
        <p className="checkout-price">{priceLabel}</p>
        <p className="lead">Оплата через менеджера после подтверждения — онлайн-оплаты нет.</p>
      </div>

      <label>
        Имя
        <input value={name} onChange={(e) => setName(e.target.value)} required autoComplete="name" />
      </label>
      <label>
        Телефон
        <input
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          required
          autoComplete="tel"
          placeholder="+7…"
        />
      </label>
      <label>
        Telegram (необязательно)
        <input
          value={telegram}
          onChange={(e) => setTelegram(e.target.value)}
          placeholder="@username"
        />
      </label>

      <fieldset className="delivery-fieldset">
        <legend>Доставка</legend>
        <label className="radio">
          <input
            type="radio"
            name="delivery"
            checked={delivery === "pickup_moscow"}
            onChange={() => setDelivery("pickup_moscow")}
          />
          Самовывоз, Москва
        </label>
        <label className="radio">
          <input
            type="radio"
            name="delivery"
            checked={delivery === "cdek"}
            onChange={() => setDelivery("cdek")}
          />
          СДЭК по России
        </label>
      </fieldset>

      {needsAddress ? (
        <label>
          Город и адрес ПВЗ / доставки СДЭК
          <textarea
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            required
            rows={3}
            placeholder="Город, улица, ПВЗ…"
          />
        </label>
      ) : null}

      <label>
        Комментарий
        <textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={2} />
      </label>

      {error ? <p className="form-error">{error}</p> : null}

      <button className="btn btn-primary" type="submit" disabled={pending || !product.price}>
        {pending ? "Оформляем…" : "Оформить заказ"}
      </button>
    </form>
  );
}
