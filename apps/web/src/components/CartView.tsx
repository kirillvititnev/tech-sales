"use client";

import Link from "next/link";

import { useCart } from "@/lib/cart";
import { formatPrice } from "@/lib/api";

export function CartView({
  checkoutHref = "/checkout",
  catalogHref = "/catalog",
}: {
  checkoutHref?: string;
  catalogHref?: string;
}) {
  const { lines, total, ready, setQty, remove, pricesSyncing, priceNote } = useCart();

  if (!ready) {
    return (
      <main className="section">
        <h2>Корзина</h2>
        <p className="lead">Загрузка…</p>
      </main>
    );
  }

  if (!lines.length) {
    return (
      <main className="section">
        <h2>Корзина</h2>
        <p className="lead">Пока пусто — добавьте товары с витрины.</p>
        <Link href={catalogHref} className="btn btn-primary">
          К каталогу
        </Link>
      </main>
    );
  }

  return (
    <main className="section">
      <h2>Корзина</h2>
      <p className="lead">Можно менять количество и оформить несколько позиций одним заказом.</p>
      {pricesSyncing ? (
        <p className="lead">Сверяем цены с витриной…</p>
      ) : priceNote ? (
        <p className="lead" role="status">
          {priceNote}
        </p>
      ) : null}
      <ul className="cart-lines">
        {lines.map((l) => (
          <li key={l.productId} className="cart-line">
            <div>
              <p className="product-brand">{l.brand ?? "Техника"}</p>
              <strong>{l.title}</strong>
              <p>{formatPrice(l.price)}</p>
            </div>
            <div className="cart-line-actions">
              <button
                type="button"
                className="qty-btn"
                aria-label="Уменьшить количество"
                onClick={() => setQty(l.productId, l.quantity - 1)}
              >
                −
              </button>
              <span>{l.quantity}</span>
              <button
                type="button"
                className="qty-btn"
                aria-label="Увеличить количество"
                onClick={() => setQty(l.productId, l.quantity + 1)}
              >
                +
              </button>
              <button type="button" className="btn btn-ghost" onClick={() => remove(l.productId)}>
                Убрать
              </button>
            </div>
          </li>
        ))}
      </ul>
      <p className="checkout-price">Итого: {formatPrice(String(total))}</p>
      <div className="cta-row">
        {pricesSyncing ? (
          <button type="button" className="btn btn-primary" disabled>
            Сверяем цены…
          </button>
        ) : (
          <Link href={checkoutHref} className="btn btn-primary">
            Оформить заказ
          </Link>
        )}
        <Link href={catalogHref} className="btn btn-ghost">
          Продолжить покупки
        </Link>
      </div>
    </main>
  );
}
