"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { LoginForm, RegisterForm } from "@/components/AuthForms";
import { ProductGrid } from "@/components/ProductGrid";
import { formatPrice, type Order, type Product } from "@/lib/api";
import { useAuth, type AccountNotification, type Me } from "@/lib/auth";

const STATUS_RU: Record<string, string> = {
  placed: "Оформлен",
  paid: "Оплачен",
  cancelled: "Отменён",
  ready: "Готов к выдаче",
  issued: "Выдан",
};

function bonusLabel(value: string | number | null | undefined): string {
  return formatPrice(value == null ? "0" : String(value));
}

function ProfileForm({ me }: { me: Me }) {
  const { patchMe, logout } = useAuth();
  const [name, setName] = useState(me.name ?? "");
  const [phone, setPhone] = useState(me.phone ?? "");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    setName(me.name ?? "");
    setPhone(me.phone ?? "");
  }, [me.name, me.phone]);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    setError(null);
    setPending(true);
    try {
      await patchMe({ name, phone });
      setMessage("Сохранено");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="checkout-form" onSubmit={onSave}>
      {me.email ? (
        <p className="lead">
          Email: <strong>{me.email}</strong>
        </p>
      ) : null}
      {me.telegram_id ? (
        <p className="lead">
          Telegram id: <strong>{me.telegram_id}</strong>
        </p>
      ) : null}
      <label>
        Имя
        <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
      </label>
      <label>
        Телефон
        <input value={phone} onChange={(e) => setPhone(e.target.value)} autoComplete="tel" />
      </label>
      {error ? <p className="form-error">{error}</p> : null}
      {message ? <p className="lead">{message}</p> : null}
      <div className="cta-row">
        <button className="btn btn-primary" type="submit" disabled={pending}>
          {pending ? "Сохраняем…" : "Сохранить"}
        </button>
        <button className="btn btn-ghost" type="button" onClick={() => void logout()}>
          Выйти
        </button>
      </div>
    </form>
  );
}

function PrivacyBlock({ me }: { me: Me }) {
  const { exportMyData, deleteAccount } = useAuth();
  const [busy, setBusy] = useState<"export" | "delete" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [password, setPassword] = useState("");

  async function onExport() {
    setError(null);
    setBusy("export");
    try {
      const data = await exportMyData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "whiteshop-data.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось выгрузить данные");
    } finally {
      setBusy(null);
    }
  }

  async function onDelete() {
    setError(null);
    setBusy("delete");
    try {
      await deleteAccount(me.email ? password : undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось удалить кабинет");
      setBusy(null);
    }
  }

  return (
    <div className="account-group">
      <h3>Данные и согласие</h3>
      <p className="account-note">
        Можно выгрузить копию кабинета или удалить профиль. Заказы магазин хранит для претензий.
      </p>
      <div className="cta-row">
        <button type="button" className="btn btn-ghost" onClick={() => void onExport()} disabled={busy !== null}>
          {busy === "export" ? "Готовим файл…" : "Скачать мои данные"}
        </button>
        {!confirmDelete ? (
          <button type="button" className="btn btn-ghost" onClick={() => setConfirmDelete(true)}>
            Удалить кабинет
          </button>
        ) : null}
      </div>
      {confirmDelete ? (
        <div className="account-danger">
          <p className="account-note">Кабинет, избранное и история просмотров будут стёрты. Это нельзя отменить.</p>
          {me.email ? (
            <label>
              Текущий пароль
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
          ) : null}
          <div className="cta-row">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => void onDelete()}
              disabled={busy !== null || (Boolean(me.email) && password.length < 8)}
            >
              {busy === "delete" ? "Удаляем…" : "Точно удалить"}
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                setConfirmDelete(false);
                setPassword("");
              }}
            >
              Отмена
            </button>
          </div>
        </div>
      ) : null}
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function ReferralBlock({ me }: { me: Me }) {
  const [copied, setCopied] = useState(false);
  const link = useMemo(() => {
    if (typeof window === "undefined") return me.referral_code;
    return `${window.location.origin}/?ref=${encodeURIComponent(me.referral_code)}`;
  }, [me.referral_code]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="account-group">
      <h3>Бонусы и рефералка</h3>
      <div className="account-row">
        <span>Баланс</span>
        <strong>{bonusLabel(me.bonus_balance)}</strong>
      </div>
      <div className="account-row">
        <span>Код</span>
        <strong>{me.referral_code}</strong>
      </div>
      <p className="account-note">
        Три уровня кэшбэка на внутренний счёт, когда приглашённый оплачивает заказ. Проценты задаёт
        магазин.
      </p>
      <button type="button" className="btn btn-ghost" onClick={copy}>
        {copied ? "Ссылка скопирована" : "Скопировать реферальную ссылку"}
      </button>
    </div>
  );
}

export function AccountCabinet({
  productBasePath = "/product",
  catalogHref = "/catalog",
  loginNext = "/account",
}: {
  productBasePath?: string;
  catalogHref?: string;
  loginNext?: string;
}) {
  const { me, ready, loadOrders, loadFavorites, loadViews, loadNotifications, markNotificationRead } =
    useAuth();
  const isMini = productBasePath.startsWith("/mini");
  const loginHref = isMini ? "/mini/account" : `/login?next=${encodeURIComponent(loginNext)}`;
  const registerHref = isMini ? "/mini/register" : `/register?next=${encodeURIComponent(loginNext)}`;
  const [mode, setMode] = useState<"login" | "register">("login");
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [favorites, setFavorites] = useState<Product[] | null>(null);
  const [views, setViews] = useState<Product[] | null>(null);
  const [notes, setNotes] = useState<AccountNotification[] | null>(null);

  useEffect(() => {
    if (!me) return;
    let cancelled = false;
    (async () => {
      try {
        const [nextOrders, nextFav, nextViews, nextNotes] = await Promise.all([
          loadOrders(),
          loadFavorites(),
          loadViews(),
          loadNotifications(),
        ]);
        if (cancelled) return;
        setOrders(nextOrders);
        setFavorites(nextFav);
        setViews(nextViews);
        setNotes(nextNotes);
      } catch {
        if (!cancelled) {
          setOrders([]);
          setFavorites([]);
          setViews([]);
          setNotes([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [me, loadOrders, loadFavorites, loadViews, loadNotifications]);

  if (!ready) {
    return (
      <main className="section">
        <h2>Кабинет</h2>
        <p className="lead">Загрузка…</p>
      </main>
    );
  }

  if (!me) {
    return (
      <main className="section">
        <h2>{mode === "register" ? "Регистрация" : "Вход"}</h2>
        <p className="lead">Telegram Login или email и пароль. Заказы, избранное и бонусы — после входа.</p>
        {isMini ? (
          <div className="segmented" role="tablist" aria-label="Вход или регистрация">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "login"}
              className={mode === "login" ? "is-active" : undefined}
              onClick={() => setMode("login")}
            >
              Вход
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "register"}
              className={mode === "register" ? "is-active" : undefined}
              onClick={() => setMode("register")}
            >
              Регистрация
            </button>
          </div>
        ) : null}
        {isMini && mode === "login" ? (
          <LoginForm nextHref={loginNext} registerHref={registerHref} />
        ) : isMini && mode === "register" ? (
          <RegisterForm nextHref={loginNext} loginHref={loginHref} />
        ) : mode === "register" ? (
          <RegisterForm nextHref={loginNext} loginHref={loginHref} />
        ) : (
          <LoginForm nextHref={loginNext} registerHref={registerHref} />
        )}
      </main>
    );
  }

  return (
    <main className="section account-page">
      <h2>Кабинет</h2>
      <p className="lead">Профиль, заказы, избранное, история и бонусы.</p>

      <div className="account-groups">
        <div className="account-group">
          <h3>Профиль</h3>
          <ProfileForm me={me} />
        </div>
        <ReferralBlock me={me} />
        <PrivacyBlock me={me} />

        <div className="account-group">
          <h3>Заказы</h3>
          {!orders?.length ? (
            <p className="account-note">
              Пока пусто. <Link href={catalogHref}>В каталог</Link>
            </p>
          ) : (
            <ul className="account-list">
              {orders.map((order) => (
                <li key={order.id}>
                  <Link
                    href={`${isMini ? "/mini/order" : "/order"}/${encodeURIComponent(order.number)}`}
                    className="account-row"
                  >
                    <span>
                      {order.number}
                      <span className="account-meta">
                        {STATUS_RU[order.customer_status] ?? order.customer_status}
                      </span>
                    </span>
                    <strong>{formatPrice(order.total_amount)}</strong>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="account-group">
          <h3>Уведомления</h3>
          {!notes?.length ? (
            <p className="account-note">Нет уведомлений.</p>
          ) : (
            <ul className="account-list">
              {notes.map((note) => (
                <li key={note.id}>
                  <button
                    type="button"
                    className={note.read_at ? "account-note-btn" : "account-note-btn is-unread"}
                    onClick={() => {
                      if (!note.read_at) {
                        void markNotificationRead(note.id).then(() =>
                          setNotes((prev) =>
                            (prev ?? []).map((item) =>
                              item.id === note.id ? { ...item, read_at: new Date().toISOString() } : item,
                            ),
                          ),
                        );
                      }
                    }}
                  >
                    <strong>{note.title}</strong>
                    <span>{note.body}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <section className="account-section">
        <h3>Избранное</h3>
        <ProductGrid
          products={favorites ?? []}
          productBasePath={productBasePath}
          emptyHref={catalogHref}
          emptyLabel="В каталог"
          emptyText="В избранном пока пусто."
        />
      </section>
      <section className="account-section">
        <h3>История просмотров</h3>
        <ProductGrid
          products={views ?? []}
          productBasePath={productBasePath}
          emptyHref={catalogHref}
          emptyLabel="В каталог"
          emptyText="История просмотров появится после открытия карточек."
        />
      </section>
    </main>
  );
}
