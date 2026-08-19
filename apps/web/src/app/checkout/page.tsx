import Link from "next/link";
import { notFound } from "next/navigation";

import { CheckoutForm } from "@/components/CheckoutForm";
import { api } from "@/lib/api";

export default async function CheckoutPage({
  searchParams,
}: {
  searchParams: Promise<{ product?: string }>;
}) {
  const { product: slug } = await searchParams;
  if (!slug) {
    return (
      <main className="section">
        <h2>Оформление</h2>
        <p className="lead">Выберите товар в каталоге, затем нажмите «Заказать».</p>
        <Link href="/#catalog" className="btn btn-primary">
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
      <CheckoutForm product={product} />
    </main>
  );
}
