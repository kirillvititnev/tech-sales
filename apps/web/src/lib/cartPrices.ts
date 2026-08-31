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

export type CartPendingChange = {
  productId: string;
  title: string;
  kind: "increase" | "removed";
  oldPrice: string | null;
  newPrice: string | null;
};

export type MergeLiveCartResult = {
  next: CartLine[];
  droppedPrices: number;
  pending: CartPendingChange[];
};

function cents(value: string | null | undefined): number | null {
  if (value == null || value === "") return null;
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return Math.round(n * 100);
}

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
  let droppedPrices = 0;
  const pending: CartPendingChange[] = [];
  const next = prev.flatMap((line) => {
    if (!requested.has(line.productId)) {
      return [line];
    }
    const product = byId.get(line.productId);
    if (!product || product.price == null) {
      pending.push({
        productId: line.productId,
        title: line.title,
        kind: "removed",
        oldPrice: line.price,
        newPrice: null,
      });
      return [line];
    }
    const price = String(product.price);
    const oldCents = cents(line.price);
    const newCents = cents(price);
    const updated: CartLine = {
      ...line,
      slug: product.slug,
      title: product.title,
      brand: product.brand,
    };
    if (oldCents != null && newCents != null && newCents < oldCents) {
      droppedPrices += 1;
      return [{ ...updated, price }];
    }
    if (oldCents == null || newCents == null || newCents > oldCents) {
      pending.push({
        productId: line.productId,
        title: product.title,
        kind: "increase",
        oldPrice: line.price,
        newPrice: price,
      });
      return [line];
    }
    return [updated];
  });
  return { next, droppedPrices, pending };
}

export function acceptCartPending(lines: CartLine[], pending: CartPendingChange[]): CartLine[] {
  const byId = new Map(pending.map((item) => [item.productId, item]));
  return lines.flatMap((line) => {
    const change = byId.get(line.productId);
    if (!change) return [line];
    if (change.kind === "removed" || change.newPrice == null) return [];
    return [{ ...line, title: change.title, price: change.newPrice }];
  });
}

export function livePriceNote(droppedPrices: number): string | null {
  if (droppedPrices <= 0) return null;
  return droppedPrices === 1 ? "Цена снижена с витрины." : "Цены снижены с витрины.";
}
