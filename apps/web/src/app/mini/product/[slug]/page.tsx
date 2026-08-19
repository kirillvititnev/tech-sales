import Link from "next/link";
import { notFound } from "next/navigation";

import { api, formatPrice } from "@/lib/api";

export default async function MiniProductPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  let product: Awaited<ReturnType<typeof api.product>>;
  try {
    product = await api.product(slug);
  } catch {
    notFound();
  }

  return (
    <main className="section">
      <p className="product-brand">{product.brand ?? "Техника"}</p>
      <h2>{product.title}</h2>
      <p className="lead">{product.description ?? "Менеджер подтвердит заказ и оплату лично."}</p>
      <p style={{ fontSize: "1.8rem", margin: "0 0 1.5rem" }}>
        <strong>{formatPrice(product.price)}</strong>
      </p>
      <div className="cta-row">
        <Link
          href={`/mini/checkout?product=${encodeURIComponent(product.slug)}`}
          className="btn btn-primary"
        >
          Заказать
        </Link>
        <Link href="/mini" className="btn btn-ghost" style={{ borderColor: "var(--line)", color: "var(--ink)" }}>
          К каталогу
        </Link>
      </div>
    </main>
  );
}
