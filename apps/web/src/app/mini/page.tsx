import { ProductGrid } from "@/components/ProductGrid";
import { api } from "@/lib/api";

export default async function MiniHomePage() {
  let products: Awaited<ReturnType<typeof api.products>> = [];
  let apiUp = true;
  try {
    products = await api.products();
  } catch {
    apiUp = false;
  }

  return (
    <main className="section">
      <h2>Каталог</h2>
      <p className="lead">
        {apiUp
          ? "White Shop Mini App — те же цены, заказ через менеджера."
          : "API недоступен. Запустите `make api`."}
      </p>
      <ProductGrid products={products} hrefFor={(slug) => `/mini/product/${slug}`} />
    </main>
  );
}
