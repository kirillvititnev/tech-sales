import assert from "node:assert/strict";
import test from "node:test";

import { livePriceNote, mergeLiveCart, type CartLine } from "./cartPrices.ts";

const line = (over: Partial<CartLine> = {}): CartLine => ({
  productId: "a",
  slug: "iphone",
  title: "iPhone",
  brand: "Apple",
  price: "10000",
  quantity: 1,
  ...over,
});

test("updates price and title for requested ids", () => {
  const { next, changed, removed } = mergeLiveCart(
    [line()],
    [{ id: "a", slug: "iphone", title: "iPhone 17", brand: "Apple", price: "12000" }],
    ["a"],
  );
  assert.equal(removed, 0);
  assert.equal(changed, 1);
  assert.equal(next[0]?.price, "12000");
  assert.equal(next[0]?.title, "iPhone 17");
});

test("drops unpublished requested lines and keeps lines added after the request", () => {
  const { next, removed } = mergeLiveCart(
    [line(), line({ productId: "b", slug: "watch", title: "Watch" })],
    [],
    ["a"],
  );
  assert.equal(removed, 1);
  assert.equal(next.length, 1);
  assert.equal(next[0]?.productId, "b");
});

test("drops published products without a price", () => {
  const { next, removed } = mergeLiveCart(
    [line()],
    [{ id: "a", slug: "iphone", title: "iPhone", brand: "Apple", price: null }],
    ["a"],
  );
  assert.equal(removed, 1);
  assert.deepEqual(next, []);
});

test("livePriceNote covers price changes and removals", () => {
  assert.equal(livePriceNote(0, 0), null);
  assert.equal(livePriceNote(0, 1), "Цены обновлены с витрины.");
  assert.equal(livePriceNote(1, 0), "Один товар снят с витрины.");
  assert.equal(livePriceNote(2, 1), "Цены обновлены с витрины. Снято с витрины: 2.");
});
