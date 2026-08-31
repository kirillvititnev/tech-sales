"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth, type TelegramWidgetUser } from "@/lib/auth";
import { safeNextHref } from "@/lib/safeHref";

const BOT_USERNAME = (process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME ?? "").trim();

function useSafeNextHref(fallback: string): string {
  const [href, setHref] = useState(fallback);
  useEffect(() => {
    const next = new URLSearchParams(window.location.search).get("next");
    setHref(safeNextHref(next, fallback));
  }, [fallback]);
  return href;
}

function TelegramLoginButton({
  onAuth,
  onError,
  privacyConsent = false,
}: {
  onAuth: (user: TelegramWidgetUser, privacyConsent: boolean) => Promise<void>;
  onError: (message: string) => void;
  privacyConsent?: boolean;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const consentRef = useRef(privacyConsent);
  consentRef.current = privacyConsent;

  useEffect(() => {
    if (!BOT_USERNAME || !hostRef.current) return;
    const host = hostRef.current;
    const w = window as Window & { onTelegramAuth?: (user: TelegramWidgetUser) => void };
    w.onTelegramAuth = (user) => {
      void onAuth(user, consentRef.current).catch((err: unknown) => {
        onError(err instanceof Error ? err.message : "Не удалось войти через Telegram");
      });
    };
    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.async = true;
    script.setAttribute("data-telegram-login", BOT_USERNAME);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-radius", "8");
    script.setAttribute("data-request-access", "write");
    script.setAttribute("data-lang", "ru");
    script.setAttribute("data-userpic", "false");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    host.replaceChildren(script);
    return () => {
      delete w.onTelegramAuth;
      host.replaceChildren();
    };
  }, [onAuth, onError]);

  if (!BOT_USERNAME) return null;
  return <div ref={hostRef} className="telegram-login-slot" />;
}

export function LoginForm({
  nextHref,
  registerHref,
  privacyHref = "/privacy",
}: {
  nextHref: string;
  registerHref: string;
  privacyHref?: string;
}) {
  const router = useRouter();
  const { login, loginTelegramWidget } = useAuth();
  const target = useSafeNextHref(nextHref);
  const errorId = useId();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      await login(email, password);
      router.push(target);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Неверный email или пароль");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="checkout-form" onSubmit={onSubmit} noValidate={false}>
      <TelegramLoginButton onAuth={loginTelegramWidget} onError={setError} />
      <label>
        Email
        <input
          type="email"
          inputMode="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
          autoCapitalize="none"
          spellCheck={false}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
        />
      </label>
      <label>
        Пароль
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
          autoComplete="current-password"
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
        />
      </label>
      {error ? (
        <p className="form-error" id={errorId} role="alert">
          {error}
        </p>
      ) : null}
      <button className="btn btn-primary" type="submit" disabled={pending}>
        {pending ? "Входим…" : "Войти"}
      </button>
      <p className="lead">
        Нет аккаунта? <Link href={registerHref}>Регистрация</Link>
        {" · "}
        <Link href={privacyHref}>Политика ПДн</Link>
      </p>
    </form>
  );
}

export function RegisterForm({
  nextHref,
  loginHref,
  privacyHref = "/privacy",
}: {
  nextHref: string;
  loginHref: string;
  privacyHref?: string;
}) {
  const router = useRouter();
  const { register, loginTelegramWidget } = useAuth();
  const target = useSafeNextHref(nextHref);
  const errorId = useId();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [privacyConsent, setPrivacyConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!privacyConsent) {
      setError("Нужно согласие на обработку персональных данных");
      return;
    }
    setPending(true);
    try {
      await register({
        email,
        password,
        name: name.trim() || undefined,
        phone: phone.trim() || undefined,
        privacy_consent: true,
      });
      router.push(target);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось зарегистрироваться");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="checkout-form" onSubmit={onSubmit}>
      {privacyConsent ? (
        <TelegramLoginButton
          onAuth={loginTelegramWidget}
          onError={setError}
          privacyConsent={privacyConsent}
        />
      ) : (
        <p className="account-note">Отметьте согласие на ПДн, чтобы войти через Telegram.</p>
      )}
      <label>
        Email
        <input
          type="email"
          inputMode="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
          autoCapitalize="none"
          spellCheck={false}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
        />
      </label>
      <label>
        Пароль
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
          autoComplete="new-password"
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
        />
      </label>
      <label>
        Имя
        <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
      </label>
      <label>
        Телефон
        <input
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          autoComplete="tel"
          inputMode="tel"
          placeholder="+7…"
        />
      </label>
      <div className="consent">
        <label className="consent">
          <input
            type="checkbox"
            checked={privacyConsent}
            onChange={(e) => setPrivacyConsent(e.target.checked)}
            required
          />
          <span>Согласен на обработку персональных данных</span>
        </label>
        <Link href={privacyHref}>Политика конфиденциальности</Link>
      </div>
      {error ? (
        <p className="form-error" id={errorId} role="alert">
          {error}
        </p>
      ) : null}
      <button className="btn btn-primary" type="submit" disabled={pending || !privacyConsent}>
        {pending ? "Создаём…" : "Зарегистрироваться"}
      </button>
      <p className="lead">
        Уже есть аккаунт? <Link href={loginHref}>Войти</Link>
      </p>
    </form>
  );
}
