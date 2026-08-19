import assert from "node:assert/strict";
import test from "node:test";

import { prefillFromTelegramUser } from "./telegramUser.ts";

test("prefill name and @username", () => {
  const p = prefillFromTelegramUser({
    id: 1,
    first_name: "Ivan",
    last_name: "Petrov",
    username: "ivan_p",
  });
  assert.equal(p.name, "Ivan Petrov");
  assert.equal(p.telegram, "@ivan_p");
});

test("prefill empty for null", () => {
  assert.deepEqual(prefillFromTelegramUser(null), {});
});

test("username already with @", () => {
  const p = prefillFromTelegramUser({ id: 2, first_name: "A", username: "@x" });
  assert.equal(p.telegram, "@x");
});
