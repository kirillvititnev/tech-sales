"use client";

import { useState } from "react";
import Link from "next/link";

import { useCart } from "@/lib/cart";
import type { Product } from "@/lib/api";

export function AddToCartButton({
  product,
  cartHref = "/cart",
}: {
  product: Product;
  cartHref?: string;
}) {
  const { add } = useCart();
  const [added, setAdded] = useState(false);

  if (!product.price) {
    return <span className="btn btn-ghost">Нет цены</span>;
  }

  return (
    <div className="cta-row">
      <button
        type="button"
        className="btn btn-primary"
        onClick={() => {
          add({
            productId: product.id,
            slug: product.slug,
            title: product.title,
            brand: product.brand,
            price: product.price!,
          });
          setAdded(true);
        }}
      >
        {added ? "В корзине" : "В корзину"}
      </button>
      {added ? (
        <Link href={cartHref} className="btn btn-ghost">
          Перейти в корзину
        </Link>
      ) : null}
    </div>
  );
}
