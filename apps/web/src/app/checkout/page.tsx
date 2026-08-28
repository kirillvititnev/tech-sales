"use client";

import Link from "next/link";

import { CheckoutForm } from "@/components/CheckoutForm";
import { useCart } from "@/lib/cart";

export default function CheckoutPage() {
  const { lines, ready } = useCart();

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
        <p className="lead">Корзина пуста. Добавьте товары, затем оформите заказ.</p>
        <Link href="/cart" className="btn btn-primary">
          В корзину
        </Link>
      </main>
    );
  }

  return (
    <main className="section">
      <h2>Оформление заказа</h2>
      <CheckoutForm items={lines} clearCartOnSuccess />
    </main>
  );
}
