export type CartLine = {
  productId: string;
  slug: string;
  title: string;
  brand: string | null;
  price: string;
  quantity: number;
};

export type LiveProduct = {
  id: string;
  slug: string;
  title: string;
  brand: string | null;
  price: string | null;
};

export type MergeLiveCartResult = {
  next: CartLine[];
  removed: number;
  changed: number;
};

export function mergeLiveCart(
  prev: CartLine[],
  live: LiveProduct[],
  requestedIds: string[],
): MergeLiveCartResult {
  const requested = new Set(requestedIds);
  const byId = new Map(
    live
      .filter((product) => product.price != null && String(product.price) !== "")
      .map((product) => [product.id, product]),
  );
  let removed = 0;
  let changed = 0;
  const next = prev.flatMap((line) => {
    if (!requested.has(line.productId)) {
      return [line];
    }
    const product = byId.get(line.productId);
    if (!product || product.price == null) {
      removed += 1;
      return [];
    }
    const price = String(product.price);
    if (price !== String(line.price) || product.title !== line.title) {
      changed += 1;
    }
    return [
      {
        ...line,
        slug: product.slug,
        title: product.title,
        brand: product.brand,
        price,
      },
    ];
  });
  return { next, removed, changed };
}

export function livePriceNote(removed: number, changed: number): string | null {
  const parts: string[] = [];
  if (changed) parts.push("Цены обновлены с витрины.");
  if (removed === 1) parts.push("Один товар снят с витрины.");
  else if (removed > 1) parts.push(`Снято с витрины: ${removed}.`);
  return parts.join(" ") || null;
}
