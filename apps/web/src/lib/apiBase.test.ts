import assert from "node:assert/strict";
import test from "node:test";

import { productImageSrc, resolveApiUrl } from "./api.ts";

test("server uses internal FastAPI", () => {
  assert.equal(
    resolveApiUrl({ isBrowser: false, publicUrl: "https://whiteshop.tech", internalUrl: "http://127.0.0.1:8000" }),
    "http://127.0.0.1:8000",
  );
});

test("browser uses same origin so Mini App hits the public host", () => {
  assert.equal(resolveApiUrl({ isBrowser: true, publicUrl: "", internalUrl: "http://127.0.0.1:8000" }), "");
  assert.equal(resolveApiUrl({ isBrowser: true, publicUrl: "same-origin" }), "");
});

test("browser can still target an explicit public API", () => {
  assert.equal(
    resolveApiUrl({ isBrowser: true, publicUrl: "https://api.whiteshop.tech/" }),
    "https://api.whiteshop.tech",
  );
});

test("product photos stay on the same origin", () => {
  const ok = "/api/v1/catalog/media/397732c0d2f649f69a631458ec3ea5df.jpg";
  assert.equal(productImageSrc(ok), ok);
  assert.equal(productImageSrc("https://evil.example/x.jpg"), null);
  assert.equal(productImageSrc("javascript:alert(1)"), null);
  assert.equal(productImageSrc("/api/v1/catalog/media/../secrets.jpg"), null);
});
