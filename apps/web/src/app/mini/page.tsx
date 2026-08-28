import { CatalogBrowser } from "@/components/CatalogBrowser";
import { api } from "@/lib/api";

export default async function MiniHomePage() {
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
    <main className="section">
      <h2>Каталог</h2>
      <p className="lead">
        {apiUp
          ? "Поиск и фильтры. Заказ подтвердит менеджер."
          : "API недоступен. Запустите `make api`."}
      </p>
      {apiUp ? (
        <CatalogBrowser
          initialProducts={products}
          initialFacets={facets}
          productBasePath="/mini/product"
        />
      ) : null}
    </main>
  );
}
