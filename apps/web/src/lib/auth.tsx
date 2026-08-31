"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { API_URL, apiErrorMessage, type Order, type Product } from "@/lib/api";
import { ensureTelegramWebApp } from "@/lib/telegram";

const TOKEN_KEY = "whiteshop.auth.v2";
const LEGACY_TOKEN_KEY = "whiteshop.auth.v1";
const REF_KEY = "whiteshop.ref.v1";
const AUTH_CREDS: RequestInit = { cache: "no-store", credentials: "include" };

type TokenResponse = {
  access_token: string;
  refresh_token?: string;
  expires_in?: number;
};

export type Me = {
  id: string;
  email: string | null;
  name: string | null;
  phone: string | null;
  telegram_id: string | null;
  referral_code: string;
  bonus_balance: string | number;
  referred_by_id?: string | null;
  privacy_consented_at?: string | null;
};

export type AccountNotification = {
  id: string;
  kind: string;
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
};

export type TelegramWidgetUser = {
  id: number | string;
  first_name?: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number | string;
  hash: string;
};

type AuthContextValue = {
  token: string | null;
  me: Me | null;
  ready: boolean;
  favoriteIds: Set<string>;
  unreadCount: number;
  authHeaders: () => HeadersInit;
  authFetch: (path: string, init?: RequestInit) => Promise<Response>;
  login: (email: string, password: string) => Promise<void>;
  register: (input: {
    email: string;
    password: string;
    name?: string;
    phone?: string;
    privacy_consent: boolean;
  }) => Promise<void>;
  loginTelegramInit: (initData: string, privacyConsent?: boolean) => Promise<void>;
  loginTelegramWidget: (user: TelegramWidgetUser, privacyConsent?: boolean) => Promise<void>;
  logout: () => Promise<void>;
  patchMe: (patch: { name?: string; phone?: string }) => Promise<void>;
  reloadMe: () => Promise<void>;
  toggleFavorite: (productId: string) => Promise<void>;
  recordView: (productId: string) => void;
  loadOrders: () => Promise<Order[]>;
  loadFavorites: () => Promise<Product[]>;
  loadViews: () => Promise<Product[]>;
  loadNotifications: () => Promise<AccountNotification[]>;
  markNotificationRead: (id: string) => Promise<void>;
  refreshUnread: () => Promise<void>;
  exportMyData: () => Promise<unknown>;
  deleteAccount: (password?: string) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function parseUnreadPayload(data: { unread?: unknown }): number {
  const value = Number(data.unread);
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
}

function storedReferral(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const value = sessionStorage.getItem(REF_KEY);
    return value && value.trim() ? value.trim().toUpperCase() : null;
  } catch {
    return null;
  }
}

function captureReferral() {
  if (typeof window === "undefined") return;
  const ref = new URLSearchParams(window.location.search).get("ref");
  if (ref && ref.trim()) {
    sessionStorage.setItem(REF_KEY, ref.trim().toUpperCase());
  }
}

function forgetStoredTokens() {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(LEGACY_TOKEN_KEY);
  } catch {
    // ignore
  }
}

let inflightRefresh: Promise<TokenResponse | null> | null = null;
let inflightRefreshHold: number | null = null;

async function postRefresh(signal?: AbortSignal): Promise<TokenResponse | null> {
  if (inflightRefresh) return inflightRefresh;
  inflightRefresh = (async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
        method: "POST",
        ...AUTH_CREDS,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
        signal,
      });
      if (!res.ok) return null;
      const data = (await res.json()) as TokenResponse;
      return data.access_token ? data : null;
    } catch {
      return null;
    }
  })();
  try {
    return await inflightRefresh;
  } finally {
    if (inflightRefreshHold != null) window.clearTimeout(inflightRefreshHold);
    // Strict Mode remounts immediately; a second POST would replay the just-rotated
    // cookie and revoke every session.
    inflightRefreshHold = window.setTimeout(() => {
      inflightRefresh = null;
      inflightRefreshHold = null;
    }, 2000);
  }
}

async function parseError(res: Response, fallback: string): Promise<string> {
  const data = await res.json().catch(() => ({}));
  return apiErrorMessage(data, fallback);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [ready, setReady] = useState(false);
  const [favoriteIds, setFavoriteIds] = useState<Set<string>>(new Set());
  const [unreadCount, setUnreadCount] = useState(0);
  const tokenRef = useRef<string | null>(null);
  const refreshLock = useRef<Promise<string | null> | null>(null);
  tokenRef.current = token;

  const clearSession = useCallback(() => {
    forgetStoredTokens();
    tokenRef.current = null;
    setToken(null);
    setMe(null);
    setFavoriteIds(new Set());
    setUnreadCount(0);
  }, []);

  const fetchFavoriteIds = useCallback(async (access: string): Promise<Set<string>> => {
    const res = await fetch(`${API_URL}/api/v1/me/favorites`, {
      ...AUTH_CREDS,
      headers: { Authorization: `Bearer ${access}` },
    });
    if (!res.ok) return new Set();
    const products = (await res.json()) as Product[];
    return new Set(products.map((p) => p.id));
  }, []);

  const fetchMe = useCallback(async (access: string): Promise<Me> => {
    const res = await fetch(`${API_URL}/api/v1/me`, {
      ...AUTH_CREDS,
      headers: { Authorization: `Bearer ${access}` },
    });
    if (!res.ok) throw new Error(await parseError(res, "Не удалось загрузить профиль"));
    return res.json() as Promise<Me>;
  }, []);

  const fetchUnread = useCallback(async (access: string): Promise<number> => {
    const res = await fetch(`${API_URL}/api/v1/me/notifications/unread-count`, {
      ...AUTH_CREDS,
      headers: { Authorization: `Bearer ${access}` },
    });
    if (!res.ok) return 0;
    const data = (await res.json()) as { unread?: unknown };
    return parseUnreadPayload(data);
  }, []);

  const applySession = useCallback(
    async (data: TokenResponse) => {
      forgetStoredTokens();
      tokenRef.current = data.access_token;
      setToken(data.access_token);
      const profile = await fetchMe(data.access_token);
      setMe(profile);
      setFavoriteIds(await fetchFavoriteIds(data.access_token));
      setUnreadCount(await fetchUnread(data.access_token));
    },
    [fetchFavoriteIds, fetchMe, fetchUnread],
  );

  const refreshAccess = useCallback(
    async (signal?: AbortSignal): Promise<string | null> => {
      if (refreshLock.current) return refreshLock.current;
      const run = (async () => {
        const data = await postRefresh(signal);
        if (!data?.access_token) {
          clearSession();
          return null;
        }
        forgetStoredTokens();
        tokenRef.current = data.access_token;
        setToken(data.access_token);
        return data.access_token;
      })();
      refreshLock.current = run;
      try {
        return await run;
      } finally {
        refreshLock.current = null;
      }
    },
    [clearSession],
  );

  useEffect(() => {
    let cancelled = false;
    const ac = new AbortController();
    const timer = window.setTimeout(() => ac.abort(), 4000);
    (async () => {
      captureReferral();
      forgetStoredTokens();
      try {
        const access = await refreshAccess(ac.signal);
        if (!access || cancelled) return;
        const profile = await fetchMe(access);
        const favs = await fetchFavoriteIds(access);
        if (cancelled) return;
        setMe(profile);
        setFavoriteIds(favs);
        setUnreadCount(await fetchUnread(access));
      } catch {
        clearSession();
      } finally {
        window.clearTimeout(timer);
        setReady(true);
      }
    })();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [clearSession, fetchFavoriteIds, fetchMe, fetchUnread, refreshAccess]);

  useEffect(() => {
    if (!ready || token) return;
    let cancelled = false;
    (async () => {
      const wa = await ensureTelegramWebApp();
      const initData = wa?.initData;
      if (!initData || cancelled) return;
      try {
        const res = await fetch(`${API_URL}/api/v1/auth/telegram`, {
          method: "POST",
          ...AUTH_CREDS,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            init_data: initData,
            referral_code: storedReferral(),
            privacy_consent: false,
          }),
        });
        if (!res.ok) return;
        const data = (await res.json()) as TokenResponse;
        if (data.access_token && !cancelled) await applySession(data);
      } catch {
        // Stay a guest if Mini App HMAC is missing (browser QA).
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ready, token, applySession]);

  const authHeaders = useCallback((): HeadersInit => {
    const current = tokenRef.current;
    return current ? { Authorization: `Bearer ${current}` } : {};
  }, []);

  const authed = useCallback(
    async (path: string, init?: RequestInit) => {
      const send = (access: string | null) =>
        fetch(`${API_URL}${path}`, {
          ...AUTH_CREDS,
          ...init,
          headers: {
            "Content-Type": "application/json",
            ...(access ? { Authorization: `Bearer ${access}` } : {}),
            ...(init?.headers ?? {}),
          },
        });
      let res = await send(tokenRef.current);
      if (res.status === 401 && tokenRef.current) {
        const next = await refreshAccess();
        if (next) res = await send(next);
      }
      return res;
    },
    [refreshAccess],
  );

  const refreshUnread = useCallback(async () => {
    if (!tokenRef.current) {
      setUnreadCount(0);
      return;
    }
    const res = await authed("/api/v1/me/notifications/unread-count");
    if (!res.ok) {
      setUnreadCount(0);
      return;
    }
    const data = (await res.json()) as { unread?: unknown };
    setUnreadCount(parseUnreadPayload(data));
  }, [authed]);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: "POST",
        ...AUTH_CREDS,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) throw new Error(await parseError(res, "Неверный email или пароль"));
      await applySession((await res.json()) as TokenResponse);
    },
    [applySession],
  );

  const register = useCallback(
    async (input: {
      email: string;
      password: string;
      name?: string;
      phone?: string;
      privacy_consent: boolean;
    }) => {
      const res = await fetch(`${API_URL}/api/v1/auth/register`, {
        method: "POST",
        ...AUTH_CREDS,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...input, referral_code: storedReferral() }),
      });
      if (!res.ok) throw new Error(await parseError(res, "Не удалось зарегистрироваться"));
      await applySession((await res.json()) as TokenResponse);
    },
    [applySession],
  );

  const loginTelegramInit = useCallback(
    async (initData: string, privacyConsent = false) => {
      const res = await fetch(`${API_URL}/api/v1/auth/telegram`, {
        method: "POST",
        ...AUTH_CREDS,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          init_data: initData,
          referral_code: storedReferral(),
          privacy_consent: privacyConsent,
        }),
      });
      if (!res.ok) throw new Error(await parseError(res, "Недействительные данные Telegram"));
      await applySession((await res.json()) as TokenResponse);
    },
    [applySession],
  );

  const loginTelegramWidget = useCallback(
    async (user: TelegramWidgetUser, privacyConsent = false) => {
      const res = await fetch(`${API_URL}/api/v1/auth/telegram-login`, {
        method: "POST",
        ...AUTH_CREDS,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: String(user.id),
          first_name: user.first_name,
          last_name: user.last_name,
          username: user.username,
          photo_url: user.photo_url,
          auth_date: String(user.auth_date),
          hash: user.hash,
          referral_code: storedReferral(),
          privacy_consent: privacyConsent,
        }),
      });
      if (!res.ok) throw new Error(await parseError(res, "Недействительные данные Telegram"));
      await applySession((await res.json()) as TokenResponse);
    },
    [applySession],
  );

  const logout = useCallback(async () => {
    try {
      await fetch(`${API_URL}/api/v1/auth/logout`, {
        method: "POST",
        ...AUTH_CREDS,
        headers: {
          "Content-Type": "application/json",
          ...(tokenRef.current ? { Authorization: `Bearer ${tokenRef.current}` } : {}),
        },
        body: JSON.stringify({}),
      });
    } catch {
      // Local sign-out still proceeds.
    }
    inflightRefresh = null;
    if (inflightRefreshHold != null) {
      window.clearTimeout(inflightRefreshHold);
      inflightRefreshHold = null;
    }
    clearSession();
  }, [clearSession]);

  const patchMe = useCallback(
    async (patch: { name?: string; phone?: string }) => {
      const res = await authed("/api/v1/me", { method: "PATCH", body: JSON.stringify(patch) });
      if (!res.ok) throw new Error(await parseError(res, "Не удалось сохранить профиль"));
      setMe((await res.json()) as Me);
    },
    [authed],
  );

  const reloadMe = useCallback(async () => {
    const access = tokenRef.current;
    if (!access) return;
    try {
      setMe(await fetchMe(access));
    } catch {
      // Keep the last known profile if refresh fails mid-checkout.
    }
  }, [fetchMe]);

  const toggleFavorite = useCallback(
    async (productId: string) => {
      if (!tokenRef.current) throw new Error("Нужен вход");
      const has = favoriteIds.has(productId);
      if (has) {
        const res = await authed(`/api/v1/me/favorites/${productId}`, { method: "DELETE" });
        if (!res.ok && res.status !== 204) throw new Error(await parseError(res, "Не удалось убрать из избранного"));
        setFavoriteIds((prev) => {
          const next = new Set(prev);
          next.delete(productId);
          return next;
        });
        return;
      }
      const res = await authed("/api/v1/me/favorites", {
        method: "POST",
        body: JSON.stringify({ product_id: productId }),
      });
      if (!res.ok) throw new Error(await parseError(res, "Не удалось добавить в избранное"));
      setFavoriteIds((prev) => new Set(prev).add(productId));
    },
    [authed, favoriteIds],
  );

  const recordView = useCallback(
    (productId: string) => {
      if (!tokenRef.current) return;
      void authed("/api/v1/me/views", {
        method: "POST",
        body: JSON.stringify({ product_id: productId }),
      });
    },
    [authed],
  );

  const loadOrders = useCallback(async () => {
    const res = await authed("/api/v1/me/orders");
    if (!res.ok) throw new Error(await parseError(res, "Не удалось загрузить заказы"));
    return res.json() as Promise<Order[]>;
  }, [authed]);

  const loadFavorites = useCallback(async () => {
    const res = await authed("/api/v1/me/favorites");
    if (!res.ok) throw new Error(await parseError(res, "Не удалось загрузить избранное"));
    const products = (await res.json()) as Product[];
    setFavoriteIds(new Set(products.map((p) => p.id)));
    return products;
  }, [authed]);

  const loadViews = useCallback(async () => {
    const res = await authed("/api/v1/me/views");
    if (!res.ok) throw new Error(await parseError(res, "Не удалось загрузить историю"));
    return res.json() as Promise<Product[]>;
  }, [authed]);

  const loadNotifications = useCallback(async () => {
    const res = await authed("/api/v1/me/notifications");
    if (!res.ok) throw new Error(await parseError(res, "Не удалось загрузить уведомления"));
    return res.json() as Promise<AccountNotification[]>;
  }, [authed]);

  const markNotificationRead = useCallback(
    async (id: string) => {
      const res = await authed(`/api/v1/me/notifications/${id}/read`, { method: "POST" });
      if (!res.ok) throw new Error(await parseError(res, "Не удалось отметить уведомление"));
      setUnreadCount((count) => Math.max(0, count - 1));
    },
    [authed],
  );

  const exportMyData = useCallback(async () => {
    const res = await authed("/api/v1/me/export");
    if (!res.ok) throw new Error(await parseError(res, "Не удалось выгрузить данные"));
    return res.json() as Promise<unknown>;
  }, [authed]);

  const deleteAccount = useCallback(
    async (password?: string) => {
      const res = await authed("/api/v1/me/delete", {
        method: "POST",
        body: JSON.stringify({ confirm: true, ...(password ? { password } : {}) }),
      });
      if (!res.ok) throw new Error(await parseError(res, "Не удалось удалить кабинет"));
      clearSession();
    },
    [authed, clearSession],
  );

  useEffect(() => {
    if (!ready || !me) return;
    const onFocus = () => {
      if (document.visibilityState === "hidden") return;
      void refreshUnread();
    };
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onFocus);
    return () => {
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onFocus);
    };
  }, [ready, me, refreshUnread]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      me,
      ready,
      favoriteIds,
      unreadCount,
      authHeaders,
      authFetch: authed,
      login,
      register,
      loginTelegramInit,
      loginTelegramWidget,
      logout,
      patchMe,
      reloadMe,
      toggleFavorite,
      recordView,
      loadOrders,
      loadFavorites,
      loadViews,
      loadNotifications,
      markNotificationRead,
      refreshUnread,
      exportMyData,
      deleteAccount,
    }),
    [
      token,
      me,
      ready,
      favoriteIds,
      unreadCount,
      authHeaders,
      authed,
      login,
      register,
      loginTelegramInit,
      loginTelegramWidget,
      logout,
      patchMe,
      reloadMe,
      toggleFavorite,
      recordView,
      loadOrders,
      loadFavorites,
      loadViews,
      loadNotifications,
      markNotificationRead,
      refreshUnread,
      exportMyData,
      deleteAccount,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("AuthProvider missing");
  return ctx;
}
