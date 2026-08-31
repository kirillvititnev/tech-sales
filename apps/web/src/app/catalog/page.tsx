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
      {!apiUp ? (
        <p className="lead">API пока недоступен — запустите `make up` и `make api`.</p>
      ) : (
        <CatalogBrowser initialProducts={products} initialFacets={facets} />
      )}
    </main>
  );
}
