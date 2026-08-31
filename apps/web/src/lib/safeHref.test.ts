import assert from "node:assert/strict";
import test from "node:test";

import { safeNextHref } from "./safeHref.ts";

test("same-origin paths stay", () => {
  assert.equal(safeNextHref("/account", "/"), "/account");
  assert.equal(safeNextHref("/mini/account", "/"), "/mini/account");
  assert.equal(safeNextHref("/catalog?q=iphone", "/"), "/catalog?q=iphone");
});

test("open redirects are dropped", () => {
  assert.equal(safeNextHref("https://evil.test", "/account"), "/account");
  assert.equal(safeNextHref("//evil.test", "/account"), "/account");
  assert.equal(safeNextHref("/\\evil.test", "/account"), "/account");
  assert.equal(safeNextHref("/%2f%2fevil.test", "/account"), "/account");
  assert.equal(safeNextHref("/admin", "/account"), "/account");
});
