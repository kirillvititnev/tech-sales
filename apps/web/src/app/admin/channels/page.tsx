"use client";

import { useEffect, useState } from "react";

import { API_URL } from "@/lib/api";

type Channel = {
  id: string;
  title: string;
  telegram_id: string;
  username: string | null;
  folder_label: string | null;
  status: string;
  last_parsed_at: string | null;
  last_error: string | null;
};

const STATUS_RU: Record<string, string> = {
  active: "Активен",
  paused: "Пауза",
  error: "Ошибка",
};

export default function AdminChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function load() {
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/channels`, { cache: "no-store" });
      if (!res.ok) throw new Error("fail");
      setChannels(await res.json());
      setError(null);
    } catch {
      setError("Не удалось загрузить каналы");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function setStatus(id: string, status: string) {
    setBusy(id);
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/channels/${id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(typeof data.detail === "string" ? data.detail : "Ошибка статуса");
        return;
      }
      const updated = await res.json();
      setChannels((prev) => prev.map((c) => (c.id === id ? { ...c, ...updated } : c)));
    } catch {
      setError("Сеть недоступна");
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="section">
      <h2>Каналы</h2>
      <p className="lead">Поставщики Telegram: статус, последняя синхронизация, ошибки.</p>
      {error ? <p className="form-error">{error}</p> : null}
      <table className="admin-table">
        <thead>
          <tr>
            <th>Канал</th>
            <th>Папка</th>
            <th>Статус</th>
            <th>Парсинг</th>
            <th>Ошибка</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {channels.length === 0 ? (
            <tr>
              <td colSpan={6}>Каналов нет — запустите `make sync-apple`</td>
            </tr>
          ) : (
            channels.map((c) => (
              <tr key={c.id}>
                <td>
                  {c.title}
                  <br />
                  <span style={{ color: "var(--mute)" }}>{c.username ? `@${c.username}` : c.telegram_id}</span>
                </td>
                <td>{c.folder_label ?? "—"}</td>
                <td>{STATUS_RU[c.status] ?? c.status}</td>
                <td>{c.last_parsed_at ? new Date(c.last_parsed_at).toLocaleString("ru-RU") : "—"}</td>
                <td style={{ maxWidth: 220, fontSize: "0.85rem", color: "var(--mute)" }}>
                  {c.last_error ?? "—"}
                </td>
                <td>
                  <div className="admin-actions">
                    {c.status !== "paused" ? (
                      <button
                        type="button"
                        className="btn btn-ghost admin-btn"
                        disabled={busy === c.id}
                        onClick={() => setStatus(c.id, "paused")}
                      >
                        Пауза
                      </button>
                    ) : null}
                    {c.status !== "active" ? (
                      <button
                        type="button"
                        className="btn btn-ghost admin-btn"
                        disabled={busy === c.id}
                        onClick={() => setStatus(c.id, "active")}
                      >
                        Вкл
                      </button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </main>
  );
}
