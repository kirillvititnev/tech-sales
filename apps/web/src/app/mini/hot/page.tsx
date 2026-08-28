import { ProductGrid } from "@/components/ProductGrid";
import { api } from "@/lib/api";

export default async function MiniHotPage() {
  let products: Awaited<ReturnType<typeof api.products>> = [];
  try {
    products = await api.products({ hot: true });
  } catch {
    products = [];
  }

  return (
    <main className="section">
      <h2>HOT</h2>
      <p className="lead">Горячие позиции.</p>
      <ProductGrid products={products} productBasePath="/mini/product" emptyHref="/mini" />
    </main>
  );
}
