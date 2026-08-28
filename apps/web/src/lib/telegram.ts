"use client";

import { useEffect, useState } from "react";

import {
  isTelegramUser,
  prefillFromTelegramUser,
  type CheckoutPrefill,
  type TelegramWebAppUser,
} from "@/lib/telegramUser";

type TelegramWebApp = {
  ready: () => void;
  expand: () => void;
  initData?: string;
  initDataUnsafe?: { user?: TelegramWebAppUser };
  colorScheme?: "light" | "dark";
  themeParams?: Record<string, string>;
};

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

const SCRIPT_SRC = "https://telegram.org/js/telegram-web-app.js";

function loadScript(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (window.Telegram?.WebApp) return Promise.resolve();
  const existing = document.querySelector<HTMLScriptElement>(`script[src="${SCRIPT_SRC}"]`);
  if (existing) {
    return new Promise((resolve) => {
      existing.addEventListener("load", () => resolve());
      if (window.Telegram?.WebApp) resolve();
    });
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Telegram WebApp script failed"));
    document.head.appendChild(script);
  });
}

export function useTelegramPrefill(): { prefill: CheckoutPrefill; inTelegram: boolean; ready: boolean } {
  const [prefill, setPrefill] = useState<CheckoutPrefill>({});
  const [inTelegram, setInTelegram] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await loadScript();
      } catch {
        // Browser QA without Telegram
      }
      if (cancelled) return;
      const wa = window.Telegram?.WebApp;
      if (wa) {
        try {
          wa.ready();
          wa.expand();
        } catch {
          // ignore
        }
        setInTelegram(true);
        const user = wa.initDataUnsafe?.user;
        if (isTelegramUser(user)) {
          setPrefill(prefillFromTelegramUser(user));
        }
        if (wa.colorScheme === "dark") {
          document.documentElement.dataset.tgTheme = "dark";
        }
      }
      setReady(true);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { prefill, inTelegram, ready };
}
