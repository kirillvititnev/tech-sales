"use client";

import { useEffect, useState } from "react";

import { API_URL } from "@/lib/api";
import { adminFetch } from "@/lib/adminFetch";

type Channel = {
  id: string;
  title: string;
  telegram_id: string;
  username: string | null;
  folder_label: string | null;
  status: string;
  last_parsed_at: string | null;
  last_error: string | null;
  counts_toward_price: boolean;
};

const STATUS_RU: Record<string, string> = {
  active: "Активен",
  paused: "Пауза",
  error: "Ошибка",
};

function formatSyncStats(stats: Record<string, unknown> | null): string | null {
  if (!stats) return null;
  const folder = typeof stats.folder === "string" ? stats.folder : null;
  const finished = typeof stats.finished_at === "string" ? stats.finished_at : null;
  if (!folder && !finished) return null;
  const when = finished ? new Date(finished).toLocaleString("ru-RU") : "—";
  const products = typeof stats.products === "number" ? stats.products : 0;
  const quarantined = typeof stats.quarantined === "number" ? stats.quarantined : 0;
  return `последний синк: ${folder ?? "каталог"} · ${when} · карточек ${products} · отброшено ${quarantined}`;
}

export default function AdminChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [syncBlurb, setSyncBlurb] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function load() {
    try {
      const [channelRes, settingsRes] = await Promise.all([
        adminFetch(`${API_URL}/api/v1/admin/channels`),
        adminFetch(`${API_URL}/api/v1/admin/settings`),
      ]);
      if (!channelRes.ok) throw new Error("fail");
      setChannels(await channelRes.json());
      if (settingsRes.ok) {
        const settings = await settingsRes.json();
        setSyncBlurb(formatSyncStats(settings.last_sync_stats ?? null));
      }
      setError(null);
    } catch {
      setError("Не удалось загрузить каналы");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function patchChannel(
    id: string,
    body: { status: string; counts_toward_price?: boolean },
  ) {
    setBusy(id);
    try {
      const res = await adminFetch(`${API_URL}/api/v1/admin/channels/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(typeof data.detail === "string" ? data.detail : "Ошибка статуса");
        return;
      }
      const updated = await res.json();
      setChannels((prev) => prev.map((c) => (c.id === id ? { ...c, ...updated } : c)));
      setError(null);
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
      {syncBlurb ? <p className="account-note">{syncBlurb}</p> : null}
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      <table className="admin-table">
        <thead>
          <tr>
            <th>Канал</th>
            <th>Папка</th>
            <th>Статус</th>
            <th>Медиана</th>
            <th>Парсинг</th>
            <th>Ошибка</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {channels.length === 0 ? (
            <tr>
              <td colSpan={7}>Каналов нет — запустите `make sync-apple`</td>
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
                <td>{c.counts_toward_price === false ? "не кормить" : "в медиане"}</td>
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
                        onClick={() => void patchChannel(c.id, { status: "paused" })}
                      >
                        Пауза
                      </button>
                    ) : null}
                    {c.status !== "active" ? (
                      <button
                        type="button"
                        className="btn btn-ghost admin-btn"
                        disabled={busy === c.id}
                        onClick={() => void patchChannel(c.id, { status: "active" })}
                      >
                        Вкл
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className="btn btn-ghost admin-btn"
                      disabled={busy === c.id}
                      onClick={() =>
                        void patchChannel(c.id, {
                          status: c.status,
                          counts_toward_price: c.counts_toward_price === false,
                        })
                      }
                    >
                      {c.counts_toward_price === false ? "В медиане" : "Не кормить медиану"}
                    </button>
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
