import Link from "next/link";
import { notFound } from "next/navigation";

import { MiniCheckoutClient } from "@/components/MiniCheckoutClient";
import { api } from "@/lib/api";

export default async function MiniCheckoutPage({
  searchParams,
}: {
  searchParams: Promise<{ product?: string }>;
}) {
  const { product: slug } = await searchParams;
  if (!slug) {
    return (
      <main className="section">
        <h2>Оформление</h2>
        <p className="lead">Выберите товар в каталоге.</p>
        <Link href="/mini" className="btn btn-primary">
          К каталогу
        </Link>
      </main>
    );
  }

  let product: Awaited<ReturnType<typeof api.product>>;
  try {
    product = await api.product(slug);
  } catch {
    notFound();
  }

  return (
    <main className="section">
      <h2>Оформление заказа</h2>
      <MiniCheckoutClient product={product} />
    </main>
  );
}
