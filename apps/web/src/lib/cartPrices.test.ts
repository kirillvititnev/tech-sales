import assert from "node:assert/strict";
import test from "node:test";

import {
  acceptCartPending,
  livePriceNote,
  mergeLiveCart,
  type CartLine,
} from "./cartPrices.ts";

const line = (over: Partial<CartLine> = {}): CartLine => ({
  productId: "a",
  slug: "iphone",
  title: "iPhone",
  brand: "Apple",
  price: "10000",
  quantity: 1,
  ...over,
});

test("applies a price drop immediately", () => {
  const { next, droppedPrices, pending } = mergeLiveCart(
    [line({ price: "12000" })],
    [{ id: "a", slug: "iphone", title: "iPhone 17", brand: "Apple", price: "10000" }],
    ["a"],
  );
  assert.equal(droppedPrices, 1);
  assert.equal(pending.length, 0);
  assert.equal(next[0]?.price, "10000");
  assert.equal(next[0]?.title, "iPhone 17");
});

test("holds a price increase until the shopper consents", () => {
  const { next, droppedPrices, pending } = mergeLiveCart(
    [line()],
    [{ id: "a", slug: "iphone", title: "iPhone 17", brand: "Apple", price: "12000" }],
    ["a"],
  );
  assert.equal(droppedPrices, 0);
  assert.equal(next[0]?.price, "10000");
  assert.equal(pending.length, 1);
  assert.equal(pending[0]?.kind, "increase");
  assert.equal(pending[0]?.newPrice, "12000");
});

test("keeps unpublished lines until the shopper removes them", () => {
  const { next, pending } = mergeLiveCart(
    [line(), line({ productId: "b", slug: "watch", title: "Watch" })],
    [],
    ["a"],
  );
  assert.equal(next.length, 2);
  assert.equal(pending.length, 1);
  assert.equal(pending[0]?.kind, "removed");
  assert.equal(pending[0]?.productId, "a");
});

test("treats a published product without a price as removed", () => {
  const { next, pending } = mergeLiveCart(
    [line()],
    [{ id: "a", slug: "iphone", title: "iPhone", brand: "Apple", price: null }],
    ["a"],
  );
  assert.equal(next.length, 1);
  assert.equal(pending.length, 1);
  assert.equal(pending[0]?.kind, "removed");
});

test("acceptCartPending applies increases and drops removed skus", () => {
  const accepted = acceptCartPending(
    [line(), line({ productId: "b", slug: "watch", title: "Watch", price: "5000" })],
    [
      { productId: "a", title: "iPhone 17", kind: "increase", oldPrice: "10000", newPrice: "12000" },
      { productId: "b", title: "Watch", kind: "removed", oldPrice: "5000", newPrice: null },
    ],
  );
  assert.equal(accepted.length, 1);
  assert.equal(accepted[0]?.price, "12000");
  assert.equal(accepted[0]?.title, "iPhone 17");
});

test("livePriceNote covers only auto-applied drops", () => {
  assert.equal(livePriceNote(0), null);
  assert.equal(livePriceNote(1), "Цена снижена с витрины.");
  assert.equal(livePriceNote(2), "Цены снижены с витрины.");
});
