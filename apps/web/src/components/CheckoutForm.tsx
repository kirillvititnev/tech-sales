"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useCart, type CartLine } from "@/lib/cart";
import { apiErrorMessage, formatPrice } from "@/lib/api";
import { useAuth, type Me } from "@/lib/auth";
import { stashOrderAccess } from "@/lib/orderAccess";
import type { CheckoutPrefill } from "@/lib/telegramUser";

type DeliveryType = "pickup_moscow" | "cdek";

function bonusBalance(me: Me | null): number {
  if (!me) return 0;
  const value = Number(me.bonus_balance);
  return Number.isFinite(value) && value > 0 ? value : 0;
}

function isBonusError(message: string): boolean {
  return message.toLowerCase().includes("бонус");
}

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
  const { lines, clear, pricesSyncing, priceNote, pricePending } = useCart();
  const { me, ready: authReady, authFetch, reloadMe } = useAuth();
  const [name, setName] = useState(defaults?.name ?? "");
  const [phone, setPhone] = useState("");
  const [telegram, setTelegram] = useState(defaults?.telegram ?? "");
  const [delivery, setDelivery] = useState<DeliveryType>("pickup_moscow");
  const [address, setAddress] = useState("");
  const [comment, setComment] = useState("");
  const [privacyConsent, setPrivacyConsent] = useState(false);
  const [useBonus, setUseBonus] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bonusError, setBonusError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const cartLines = lines.length ? lines : items;

  useEffect(() => {
    if (me?.name) setName(me.name);
    else if (defaults?.name) setName(defaults.name);
    if (me?.phone) setPhone(me.phone);
    if (defaults?.telegram) setTelegram(defaults.telegram);
  }, [me?.name, me?.phone, defaults?.name, defaults?.telegram]);

  const goodsTotal = useMemo(
    () => cartLines.reduce((sum, line) => sum + Number(line.price) * line.quantity, 0),
    [cartLines],
  );
  const maxBonus = Math.min(bonusBalance(me), goodsTotal);
  const spend = useBonus && maxBonus >= 0.01 ? Number(maxBonus.toFixed(2)) : 0;
  const payable = Math.max(0, goodsTotal - spend);

  useEffect(() => {
    if (maxBonus < 0.01) setUseBonus(false);
  }, [maxBonus]);

  const needsAddress = delivery === "cdek";

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBonusError(null);
    if (!cartLines.length) {
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
          ...(spend > 0 ? { bonus_spend: spend } : {}),
          items: cartLines.map((l) => ({
            product_id: l.productId,
            quantity: l.quantity,
          })),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const message = apiErrorMessage(data, "Не удалось оформить заказ");
        if (isBonusError(message)) setBonusError(message);
        else setError(message);
        return;
      }
      if (clearCartOnSuccess) clear();
      await reloadMe();
      const access = typeof data.access_token === "string" ? data.access_token : "";
      if (access) stashOrderAccess(data.number, access);
      const href = successHref ? successHref(data.number, access) : `/order/${data.number}`;
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
        <p className="product-brand">Заявка менеджеру</p>
        {pricesSyncing ? <p className="lead">Сверяем цены с витриной…</p> : null}
        {priceNote ? (
          <p className="lead" role="status">
            {priceNote}
          </p>
        ) : null}
        <p className="lead">Цена на карточке — котировка витрины, не оплаченный чек.</p>
        <ul className="cart-summary-list">
          {cartLines.map((l) => (
            <li key={l.productId}>
              {l.title} × {l.quantity} — {formatPrice(l.price)}
            </li>
          ))}
        </ul>
        {spend > 0 ? (
          <>
            <p className="lead">Товары: {formatPrice(String(goodsTotal))}</p>
            <p className="lead">Бонусы: −{formatPrice(String(spend))}</p>
          </>
        ) : null}
        <p className="checkout-price">{formatPrice(String(payable))}</p>
        <p className="lead">Оплата — только через менеджера после подтверждения. Онлайн-оплаты нет.</p>
        {authReady && !me ? (
          <p className="lead">
            <Link href={loginHref}>Войдите</Link>, чтобы заказ появился в кабинете и можно было
            списать бонусы.
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

      {authReady && me && maxBonus >= 0.01 ? (
        <fieldset className="delivery-group">
          <legend>Бонусы</legend>
          <div className="delivery-options">
            <label className="delivery-option">
              <input
                type="checkbox"
                checked={useBonus}
                onChange={(e) => {
                  setUseBonus(e.target.checked);
                  setBonusError(null);
                }}
                aria-invalid={bonusError ? true : undefined}
                aria-describedby={bonusError ? "bonus-error" : undefined}
              />
              <span className="delivery-option-text">
                <span className="delivery-option-title">
                  Списать {formatPrice(String(maxBonus))}
                </span>
                <span className="delivery-option-meta">С бонусного счёта, не больше суммы заказа</span>
              </span>
            </label>
          </div>
          {bonusError ? (
            <p id="bonus-error" className="form-error" role="alert">
              {bonusError}
            </p>
          ) : null}
        </fieldset>
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

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      <button
        className="btn btn-primary"
        type="submit"
        disabled={pending || pricesSyncing || pricePending.length > 0 || !cartLines.length || !privacyConsent}
      >
        {pending ? "Отправляем…" : "Отправить заявку"}
      </button>
    </form>
  );
}
