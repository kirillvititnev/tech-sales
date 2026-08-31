"use client";

import { FormEvent, useEffect, useState } from "react";

import { API_URL, formatPrice } from "@/lib/api";
import { adminFetch } from "@/lib/adminFetch";

type AdminUser = {
  id: string;
  email: string | null;
  name: string | null;
  phone: string | null;
  telegram_id: string | null;
  referral_code: string;
  bonus_balance: string | number;
  is_active: boolean;
  created_at: string;
};

type BonusDraft = {
  delta: string;
  note: string;
  error: string | null;
};

function emptyDraft(): BonusDraft {
  return { delta: "", note: "", error: null };
}

function apiDetail(data: unknown, fallback: string): string {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, BonusDraft>>({});

  async function load(query?: string) {
    const sp = new URLSearchParams();
    if (query) sp.set("q", query);
    try {
      const res = await adminFetch(`${API_URL}/api/v1/admin/users?${sp}`);
      if (!res.ok) throw new Error("fail");
      setUsers(await res.json());
      setError(null);
    } catch {
      setError("Не удалось загрузить пользователей");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function draftFor(id: string): BonusDraft {
    return drafts[id] ?? emptyDraft();
  }

  function setDraft(id: string, patch: Partial<BonusDraft>) {
    setDrafts((prev) => ({ ...prev, [id]: { ...emptyDraft(), ...prev[id], ...patch } }));
  }

  async function patchActive(user: AdminUser, isActive: boolean) {
    if (!isActive) {
      const ok = window.confirm("Отключить аккаунт? Все сессии будут сброшены.");
      if (!ok) return;
    }
    setBusy(true);
    try {
      const res = await adminFetch(`${API_URL}/api/v1/admin/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: isActive }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(apiDetail(data, "Не удалось обновить статус"));
        return;
      }
      const updated = (await res.json()) as AdminUser;
      setUsers((prev) => prev.map((item) => (item.id === user.id ? { ...item, ...updated } : item)));
      setError(null);
    } catch {
      setError("Сеть недоступна");
    } finally {
      setBusy(false);
    }
  }

  async function submitBonus(e: FormEvent, user: AdminUser) {
    e.preventDefault();
    const draft = draftFor(user.id);
    const delta = Number(draft.delta.replace(",", "."));
    if (!Number.isFinite(delta) || delta === 0) {
      setDraft(user.id, { error: "Укажите сумму, не равную нулю" });
      return;
    }
    if (delta < 0) {
      const ok = window.confirm(`Списать ${formatPrice(String(Math.abs(delta)))} с бонусного счёта?`);
      if (!ok) return;
    }
    setBusy(true);
    setDraft(user.id, { error: null });
    try {
      const res = await adminFetch(`${API_URL}/api/v1/admin/users/${user.id}/bonus`, {
        method: "POST",
        body: JSON.stringify({
          delta,
          note: draft.note.trim() || null,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setDraft(user.id, { error: apiDetail(data, "Не удалось изменить бонусы") });
        return;
      }
      const updated = (await res.json()) as AdminUser;
      setUsers((prev) => prev.map((item) => (item.id === user.id ? { ...item, ...updated } : item)));
      setDrafts((prev) => ({ ...prev, [user.id]: emptyDraft() }));
      setError(null);
    } catch {
      setDraft(user.id, { error: "Сеть недоступна" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="section">
      <h2>Пользователи</h2>
      <p className="lead">Поиск, бонусный счёт и отключение аккаунта. Пароли не показываются.</p>

      <form
        className="admin-search"
        onSubmit={(e) => {
          e.preventDefault();
          void load(q);
        }}
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Email, телефон, Telegram или код"
          aria-label="Поиск пользователей"
        />
        <button type="submit" className="btn btn-ghost admin-btn">
          Найти
        </button>
      </form>

      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}

      <table className="admin-table">
        <thead>
          <tr>
            <th>Клиент</th>
            <th>Бонусы</th>
            <th>Статус</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => {
            const draft = draftFor(user.id);
            const errorId = `bonus-error-${user.id}`;
            return (
              <tr key={user.id}>
                <td>
                  {user.name || user.email || "Без имени"}
                  <br />
                  <span style={{ color: "var(--mute)" }}>
                    {user.email ?? "без email"}
                    {user.phone ? ` · ${user.phone}` : ""}
                    {user.telegram_id ? ` · tg ${user.telegram_id}` : ""}
                    {` · ${user.referral_code}`}
                  </span>
                </td>
                <td>
                  <strong>{formatPrice(String(user.bonus_balance))}</strong>
                  <form className="admin-bonus" onSubmit={(e) => void submitBonus(e, user)}>
                    <label className="sr-only" htmlFor={`bonus-delta-${user.id}`}>
                      Сумма бонусов
                    </label>
                    <input
                      id={`bonus-delta-${user.id}`}
                      type="number"
                      step="1"
                      inputMode="decimal"
                      value={draft.delta}
                      onChange={(e) => setDraft(user.id, { delta: e.target.value, error: null })}
                      placeholder="±₽"
                      aria-invalid={draft.error ? true : undefined}
                      aria-describedby={draft.error ? errorId : undefined}
                      disabled={busy}
                    />
                    <label className="sr-only" htmlFor={`bonus-note-${user.id}`}>
                      Комментарий
                    </label>
                    <input
                      id={`bonus-note-${user.id}`}
                      value={draft.note}
                      onChange={(e) => setDraft(user.id, { note: e.target.value })}
                      placeholder="Комментарий"
                      maxLength={255}
                      disabled={busy}
                    />
                    <button type="submit" className="btn btn-ghost admin-btn" disabled={busy}>
                      Начислить
                    </button>
                  </form>
                  {draft.error ? (
                    <p className="form-error" id={errorId} role="alert">
                      {draft.error}
                    </p>
                  ) : null}
                </td>
                <td>{user.is_active ? "активен" : "отключён"}</td>
                <td>
                  <button
                    type="button"
                    className="btn btn-ghost admin-btn"
                    disabled={busy}
                    onClick={() => void patchActive(user, !user.is_active)}
                  >
                    {user.is_active ? "Отключить" : "Включить"}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </main>
  );
}
