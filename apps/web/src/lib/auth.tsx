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

type TokenResponse = {
  access_token: string;
  refresh_token: string;
  expires_in?: number;
};

type StoredSession = {
  access_token: string;
  refresh_token: string;
  expires_at: number;
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

function readSession(): StoredSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(TOKEN_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredSession;
    if (!parsed.access_token || !parsed.refresh_token) return null;
    return parsed;
  } catch {
    return null;
  }
}

function writeSession(data: TokenResponse): StoredSession {
  const session: StoredSession = {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    expires_at: Date.now() + Math.max(30, (data.expires_in ?? 900) - 20) * 1000,
  };
  localStorage.setItem(TOKEN_KEY, JSON.stringify(session));
  localStorage.removeItem(LEGACY_TOKEN_KEY);
  return session;
}

function clearStored() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(LEGACY_TOKEN_KEY);
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
  const refreshRef = useRef<string | null>(null);
  const refreshLock = useRef<Promise<string | null> | null>(null);
  tokenRef.current = token;

  const clearSession = useCallback(() => {
    clearStored();
    tokenRef.current = null;
    refreshRef.current = null;
    setToken(null);
    setMe(null);
    setFavoriteIds(new Set());
    setUnreadCount(0);
  }, []);

  const fetchFavoriteIds = useCallback(async (access: string): Promise<Set<string>> => {
    const res = await fetch(`${API_URL}/api/v1/me/favorites`, {
      cache: "no-store",
      headers: { Authorization: `Bearer ${access}` },
    });
    if (!res.ok) return new Set();
    const products = (await res.json()) as Product[];
    return new Set(products.map((p) => p.id));
  }, []);

  const fetchMe = useCallback(async (access: string): Promise<Me> => {
    const res = await fetch(`${API_URL}/api/v1/me`, {
      cache: "no-store",
      headers: { Authorization: `Bearer ${access}` },
    });
    if (!res.ok) throw new Error(await parseError(res, "Не удалось загрузить профиль"));
    return res.json() as Promise<Me>;
  }, []);

  const fetchUnread = useCallback(async (access: string): Promise<number> => {
    const res = await fetch(`${API_URL}/api/v1/me/notifications/unread-count`, {
      cache: "no-store",
      headers: { Authorization: `Bearer ${access}` },
    });
    if (!res.ok) return 0;
    const data = (await res.json()) as { unread?: unknown };
    return parseUnreadPayload(data);
  }, []);

  const applySession = useCallback(
    async (data: TokenResponse) => {
      const session = writeSession(data);
      tokenRef.current = session.access_token;
      refreshRef.current = session.refresh_token;
      setToken(session.access_token);
      const profile = await fetchMe(session.access_token);
      setMe(profile);
      setFavoriteIds(await fetchFavoriteIds(session.access_token));
      setUnreadCount(await fetchUnread(session.access_token));
    },
    [fetchFavoriteIds, fetchMe, fetchUnread],
  );

  const refreshAccess = useCallback(async (): Promise<string | null> => {
    if (refreshLock.current) return refreshLock.current;
    const run = (async () => {
      const session = readSession();
      const refreshToken = session?.refresh_token ?? refreshRef.current;
      if (!refreshToken) return null;
      const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) {
        clearSession();
        return null;
      }
      const data = (await res.json()) as TokenResponse;
      const next = writeSession(data);
      tokenRef.current = next.access_token;
      refreshRef.current = next.refresh_token;
      setToken(next.access_token);
      return next.access_token;
    })();
    refreshLock.current = run;
    try {
      return await run;
    } finally {
      refreshLock.current = null;
    }
  }, [clearSession]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      captureReferral();
      localStorage.removeItem(LEGACY_TOKEN_KEY);
      const stored = readSession();
      if (!stored) {
        if (!cancelled) setReady(true);
        return;
      }
      refreshRef.current = stored.refresh_token;
      try {
        let access = stored.access_token;
        if (stored.expires_at && stored.expires_at < Date.now()) {
          const next = await refreshAccess();
          if (!next) throw new Error("expired");
          access = next;
        }
        const profile = await fetchMe(access).catch(async () => {
          const next = await refreshAccess();
          if (!next) throw new Error("expired");
          return fetchMe(next);
        });
        const favs = await fetchFavoriteIds(tokenRef.current || access);
        if (cancelled) return;
        tokenRef.current = tokenRef.current || access;
        setToken(tokenRef.current);
        setMe(profile);
        setFavoriteIds(favs);
        setUnreadCount(await fetchUnread(tokenRef.current));
      } catch {
        clearSession();
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
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
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            init_data: initData,
            referral_code: storedReferral(),
            privacy_consent: false,
          }),
        });
        if (!res.ok) return;
        const data = (await res.json()) as TokenResponse;
        if (data.access_token && data.refresh_token && !cancelled) await applySession(data);
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
          cache: "no-store",
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
    const session = readSession();
    try {
      await fetch(`${API_URL}/api/v1/auth/logout`, {
        method: "POST",
        cache: "no-store",
        headers: {
          "Content-Type": "application/json",
          ...(tokenRef.current ? { Authorization: `Bearer ${tokenRef.current}` } : {}),
        },
        body: JSON.stringify(session?.refresh_token ? { refresh_token: session.refresh_token } : {}),
      });
    } catch {
      // Local sign-out still proceeds.
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
