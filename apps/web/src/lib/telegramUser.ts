export type TelegramWebAppUser = {
  id?: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  language_code?: string;
};

export type CheckoutPrefill = {
  name?: string;
  telegram?: string;
};

/** Pure helper — safe to unit-test without DOM. */
export function prefillFromTelegramUser(user: TelegramWebAppUser | null | undefined): CheckoutPrefill {
  if (!user) return {};
  const name = [user.first_name, user.last_name].filter(Boolean).join(" ").trim();
  const telegram = user.username ? `@${user.username.replace(/^@/, "")}` : undefined;
  return {
    name: name || undefined,
    telegram,
  };
}

export function isTelegramUser(value: unknown): value is TelegramWebAppUser {
  return typeof value === "object" && value !== null && "id" in value;
}
