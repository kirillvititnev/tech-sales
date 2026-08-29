import { CatalogBrowser } from "@/components/CatalogBrowser";
import { api } from "@/lib/api";

export default async function CatalogPage() {
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
          ? "Поиск, категории и фильтры. Цены уже с наценкой магазина."
          : "API пока недоступен — запустите `make up` и `make api`."}
      </p>
      {apiUp ? (
        <CatalogBrowser initialProducts={products} initialFacets={facets} />
      ) : null}
    </main>
  );
}
