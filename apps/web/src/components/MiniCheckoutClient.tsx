"use client";

import { CheckoutForm } from "@/components/CheckoutForm";
import { useTelegramPrefill } from "@/lib/telegram";
import type { Product } from "@/lib/api";

export function MiniCheckoutClient({ product }: { product: Product }) {
  const { prefill } = useTelegramPrefill();
  return (
    <CheckoutForm
      product={product}
      defaults={prefill}
      successHref={(number) => `/mini/order/${number}`}
    />
  );
}
