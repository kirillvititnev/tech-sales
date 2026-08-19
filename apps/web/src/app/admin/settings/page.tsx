"use client";

import { useEffect, useState } from "react";

import { API_URL } from "@/lib/api";

export default function AdminSettingsPage() {
  const [markup, setMarkup] = useState("10");
  const [roundTo, setRoundTo] = useState("100");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/admin/settings`, { cache: "no-store" });
        if (!res.ok) throw new Error("fail");
        const data = await res.json();
        setMarkup(String(data.default_markup_percent));
        setRoundTo(String(data.price_round_to));
      } catch {
        setError("Не удалось загрузить настройки");
      }
    })();
  }, []);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/settings`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          default_markup_percent: Number(markup),
          price_round_to: Number(roundTo),
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(typeof data.detail === "string" ? data.detail : "Ошибка сохранения");
        return;
      }
      const data = await res.json();
      setMarkup(String(data.default_markup_percent));
      setRoundTo(String(data.price_round_to));
      setMessage("Сохранено. Новые значения подхватят следующие расчёты/синки; массовый пересчёт — позже.");
    } catch {
      setError("Сеть недоступна");
    }
  }

  return (
    <main className="section">
      <h2>Наценка</h2>
      <p className="lead">Базовый фиксированный % и шаг округления витрины.</p>
      <form className="checkout-form" onSubmit={onSave}>
        <label>
          Наценка, %
          <input value={markup} onChange={(e) => setMarkup(e.target.value)} type="number" min={0} max={100} step="0.1" />
        </label>
        <label>
          Округление до, ₽
          <input value={roundTo} onChange={(e) => setRoundTo(e.target.value)} type="number" min={1} />
        </label>
        {error ? <p className="form-error">{error}</p> : null}
        {message ? <p className="lead">{message}</p> : null}
        <button type="submit" className="btn btn-primary">
          Сохранить
        </button>
      </form>
    </main>
  );
}
