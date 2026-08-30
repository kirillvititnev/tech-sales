import Link from "next/link";
import { notFound } from "next/navigation";

import { AddToCartButton } from "@/components/AddToCartButton";
import { api, formatPrice, productImageSrc } from "@/lib/api";

export default async function MiniProductPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  let product: Awaited<ReturnType<typeof api.product>>;
  try {
    product = await api.product(slug);
  } catch {
    notFound();
  }

  const attrs = product.attributes ?? {};
  const category = typeof attrs.device_category === "string" ? attrs.device_category : "";
  const name =
    typeof attrs.device_name === "string" && attrs.device_name ? attrs.device_name : product.title;
  const config = typeof attrs.config === "string" ? attrs.config : "";

  return (
    <main className="section">
      <p className="product-brand">{product.brand ?? "—"}</p>
      {category ? <p className="product-category">{category}</p> : null}
      <h2 style={{ marginTop: "0.35rem" }}>{name}</h2>
      {config ? <p className="product-config" style={{ marginTop: "0.5rem" }}>{config}</p> : null}
      {productImageSrc(product.image_url) ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          className="product-sheet-photo"
          src={productImageSrc(product.image_url) ?? ""}
          alt={name}
        />
      ) : null}
      <p className="lead">{product.description ?? "Менеджер подтвердит заказ и оплату лично."}</p>
      <p style={{ fontSize: "1.8rem", margin: "0 0 1.5rem" }}>
        <strong>{formatPrice(product.price)}</strong>
      </p>
      <AddToCartButton product={product} cartHref="/mini/cart" />
      <div className="cta-row" style={{ marginTop: "0.75rem" }}>
        <Link href="/mini" className="btn btn-ghost">
          К каталогу
        </Link>
      </div>
    </main>
  );
}
