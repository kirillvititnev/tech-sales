import Link from "next/link";

import { formatPrice, type Product } from "@/lib/api";

export function ProductGrid({
  products,
  hrefFor,
}: {
  products: Product[];
  hrefFor?: (slug: string) => string;
}) {
  if (!products.length) {
    return <p className="empty">Пока нет товаров на витрине.</p>;
  }

  const link = hrefFor ?? ((slug: string) => `/product/${slug}`);

  return (
    <div className="product-grid">
      {products.map((p) => (
        <Link key={p.id} href={link(p.slug)} className="product-row">
          <div>
            <p className="product-brand">{p.brand ?? "Техника"}</p>
            <h3>{p.title}</h3>
          </div>
          <div className="product-meta">
            {p.is_hot ? <span className="hot-tag">HOT</span> : null}
            <strong>{formatPrice(p.price)}</strong>
          </div>
        </Link>
      ))}
    </div>
  );
}
