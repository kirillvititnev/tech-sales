import Link from "next/link";

import { ProductGrid } from "@/components/ProductGrid";
import { api } from "@/lib/api";

export default async function HomePage() {
  let products: Awaited<ReturnType<typeof api.products>> = [];
  let apiUp = true;

  try {
    products = await api.products();
  } catch {
    apiUp = false;
  }

  return (
    <main>
      <section className="hero">
        <h1 className="hero-brand">White Shop</h1>
        <p>
          Автоматическая витрина техники: цены из каналов поставщиков, медиана и честная наценка.
          Москва — самовывоз, регионы — СДЭК.
        </p>
        <div className="cta-row">
          <Link href="#catalog" className="btn btn-primary">
            Смотреть каталог
          </Link>
          <Link href="/hot" className="btn btn-ghost">
            HOT предложения
          </Link>
        </div>
      </section>

      <section id="catalog" className="section">
        <h2>Каталог</h2>
        <p className="lead">
          {apiUp
            ? "Актуальные позиции с витрины."
            : "API пока недоступен — запустите `make up` и `make api`."}
        </p>
        <ProductGrid products={products} />
      </section>
    </main>
  );
}
