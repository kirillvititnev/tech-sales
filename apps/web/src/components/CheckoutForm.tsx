"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useCart, type CartLine } from "@/lib/cart";
import { formatPrice } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { CheckoutPrefill } from "@/lib/telegramUser";

type DeliveryType = "pickup_moscow" | "cdek";

export function CheckoutForm({
  items,
  defaults,
  successHref,
  loginHref = "/login?next=/checkout",
  clearCartOnSuccess = false,
}: {
  items: CartLine[];
  defaults?: CheckoutPrefill;
  successHref?: (number: string, access: string) => string;
  loginHref?: string;
  clearCartOnSuccess?: boolean;
}) {
  const router = useRouter();
  const { clear } = useCart();
  const { me, ready: authReady, authFetch } = useAuth();
  const [name, setName] = useState(defaults?.name ?? "");
  const [phone, setPhone] = useState("");
  const [telegram, setTelegram] = useState(defaults?.telegram ?? "");
  const [delivery, setDelivery] = useState<DeliveryType>("pickup_moscow");
  const [address, setAddress] = useState("");
  const [comment, setComment] = useState("");
  const [privacyConsent, setPrivacyConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (me?.name) setName(me.name);
    else if (defaults?.name) setName(defaults.name);
    if (me?.phone) setPhone(me.phone);
    if (defaults?.telegram) setTelegram(defaults.telegram);
  }, [me?.name, me?.phone, defaults?.name, defaults?.telegram]);

  const needsAddress = delivery === "cdek";
  const totalLabel = useMemo(() => {
    const sum = items.reduce((s, l) => s + Number(l.price) * l.quantity, 0);
    return formatPrice(String(sum));
  }, [items]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!items.length) {
      setError("Корзина пуста");
      return;
    }
    if (!privacyConsent) {
      setError("Нужно согласие на обработку персональных данных");
      return;
    }
    setPending(true);
    try {
      const initData =
        typeof window !== "undefined" ? window.Telegram?.WebApp?.initData ?? "" : "";
      const res = await authFetch("/api/v1/orders", {
        method: "POST",
        body: JSON.stringify({
          customer_name: name,
          customer_phone: phone,
          customer_telegram: telegram || null,
          delivery_type: delivery,
          delivery_address: needsAddress ? address : null,
          comment: comment || null,
          telegram_init_data: initData || null,
          privacy_consent: true,
          items: items.map((l) => ({
            product_id: l.productId,
            quantity: l.quantity,
          })),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Не удалось оформить заказ");
        return;
      }
      if (clearCartOnSuccess) clear();
      const access = typeof data.access_token === "string" ? data.access_token : "";
      const href = successHref
        ? successHref(data.number, access)
        : `/order/${data.number}?access=${encodeURIComponent(access)}`;
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
        <p className="product-brand">Заказ</p>
        <ul className="cart-summary-list">
          {items.map((l) => (
            <li key={l.productId}>
              {l.title} × {l.quantity} — {formatPrice(l.price)}
            </li>
          ))}
        </ul>
        <p className="checkout-price">{totalLabel}</p>
        <p className="lead">Оплата через менеджера после подтверждения — онлайн-оплаты нет.</p>
        {authReady && !me ? (
          <p className="lead">
            <Link href={loginHref}>Войдите</Link>, чтобы заказ появился в кабинете.
          </p>
        ) : null}
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
          inputMode="tel"
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

      <fieldset className="delivery-group">
        <legend>Доставка</legend>
        <div className="delivery-options">
          <label className="delivery-option">
            <input
              type="radio"
              name="delivery"
              checked={delivery === "pickup_moscow"}
              onChange={() => setDelivery("pickup_moscow")}
            />
            <span className="delivery-option-text">
              <span className="delivery-option-title">Самовывоз</span>
              <span className="delivery-option-meta">Москва</span>
            </span>
          </label>
          <label className="delivery-option">
            <input
              type="radio"
              name="delivery"
              checked={delivery === "cdek"}
              onChange={() => setDelivery("cdek")}
            />
            <span className="delivery-option-text">
              <span className="delivery-option-title">СДЭК</span>
              <span className="delivery-option-meta">По России</span>
            </span>
          </label>
        </div>
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

      <div className="consent">
        <label className="consent">
          <input
            type="checkbox"
            checked={privacyConsent}
            onChange={(e) => setPrivacyConsent(e.target.checked)}
            required
          />
          <span>Согласен на обработку персональных данных</span>
        </label>
        <Link href="/privacy">Политика конфиденциальности</Link>
      </div>

      {error ? <p className="form-error">{error}</p> : null}

      <button className="btn btn-primary" type="submit" disabled={pending || !items.length || !privacyConsent}>
        {pending ? "Оформляем…" : "Оформить заказ"}
      </button>
    </form>
  );
}
