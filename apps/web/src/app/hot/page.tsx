import { ProductGrid } from "@/components/ProductGrid";
import { api } from "@/lib/api";

export default async function HotPage() {
  let products: Awaited<ReturnType<typeof api.products>> = [];
  try {
    products = await api.products({ hot: true });
  } catch {
    products = [];
  }

  return (
    <main className="section">
      <h2>HOT</h2>
      <ProductGrid products={products} emptyHref="/catalog" />
    </main>
  );
}
