import Link from "next/link";

import { CatalogBrowser } from "@/components/CatalogBrowser";
import { api } from "@/lib/api";

export default async function HomePage() {
  let products: Awaited<ReturnType<typeof api.products>> = [];
  let facets: Awaited<ReturnType<typeof api.facets>> | null = null;
  let apiUp = true;

  try {
    [products, facets] = await Promise.all([
      api.products({ limit: 120, sort: "relevance" }),
      api.facets(),
    ]);
  } catch {
    apiUp = false;
  }

  return (
    <main>
      <section className="hero">
        <h1 className="hero-brand">White Shop</h1>
        <p>
          Автоматическая витрина техники: медиана предложений поставщиков и наценка магазина.
          Москва — самовывоз, регионы — СДЭК.
        </p>
        <div className="cta-row">
          <Link href="/catalog" className="btn btn-primary">
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
            ? "Поиск, категории, фильтры и сортировка."
            : "API пока недоступен — запустите `make up` и `make api`."}
        </p>
        {apiUp ? (
          <CatalogBrowser initialProducts={products} initialFacets={facets} />
        ) : null}
      </section>
    </main>
  );
}
