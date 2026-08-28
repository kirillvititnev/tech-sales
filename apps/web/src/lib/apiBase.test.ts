import assert from "node:assert/strict";
import test from "node:test";

import { resolveApiUrl } from "./api.ts";

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
