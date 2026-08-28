import { Suspense } from "react";

import { OrderConfirmation } from "@/components/OrderConfirmation";

export default function OrderPage() {
  return (
    <Suspense fallback={<main className="section"><h2>Заказ…</h2></main>}>
      <OrderConfirmation catalogHref="/#catalog" />
    </Suspense>
  );
}
