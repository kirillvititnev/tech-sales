"use client";

import Link from "next/link";

import { CheckoutForm } from "@/components/CheckoutForm";
import { useCart } from "@/lib/cart";
import { useTelegramPrefill } from "@/lib/telegram";

export default function MiniCheckoutPage() {
  const { lines, ready } = useCart();
  const { prefill } = useTelegramPrefill();

  if (!ready) {
    return (
      <main className="section">
        <h2>Оформление заказа</h2>
        <p className="lead">Загрузка…</p>
      </main>
    );
  }

  if (!lines.length) {
    return (
      <main className="section">
        <h2>Оформление</h2>
        <p className="lead">Корзина пуста.</p>
        <Link href="/mini/cart" className="btn btn-primary">
          В корзину
        </Link>
      </main>
    );
  }

  return (
    <main className="section">
      <h2>Оформление заказа</h2>
      <CheckoutForm
        items={lines}
        defaults={prefill}
        successHref={(number, access) =>
          `/mini/order/${number}?access=${encodeURIComponent(access)}`
        }
        clearCartOnSuccess
      />
    </main>
  );
}
