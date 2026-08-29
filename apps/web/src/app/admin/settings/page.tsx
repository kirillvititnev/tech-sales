"use client";

import { useEffect, useState } from "react";

import { API_URL } from "@/lib/api";
import { adminFetch } from "@/lib/adminFetch";

export default function AdminSettingsPage() {
  const [markup, setMarkup] = useState("0");
  const [roundTo, setRoundTo] = useState("100");
  const [l1, setL1] = useState("5");
  const [l2, setL2] = useState("2");
  const [l3, setL3] = useState("1");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await adminFetch(`${API_URL}/api/v1/admin/settings`);
        if (!res.ok) throw new Error("fail");
        const data = await res.json();
        setMarkup(String(data.default_markup_percent));
        setRoundTo(String(data.price_round_to));
        setL1(String(data.referral_percent_l1 ?? "5"));
        setL2(String(data.referral_percent_l2 ?? "2"));
        setL3(String(data.referral_percent_l3 ?? "1"));
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
      const res = await adminFetch(`${API_URL}/api/v1/admin/settings`, {
        method: "PATCH",
        body: JSON.stringify({
          default_markup_percent: Number(markup),
          price_round_to: Number(roundTo),
          referral_percent_l1: Number(l1),
          referral_percent_l2: Number(l2),
          referral_percent_l3: Number(l3),
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
      setL1(String(data.referral_percent_l1));
      setL2(String(data.referral_percent_l2));
      setL3(String(data.referral_percent_l3));
      setMessage("Сохранено. Наценка подхватит следующие синки; рефералка действует на новые оплаты.");
    } catch {
      setError("Сеть недоступна");
    }
  }

  return (
    <main className="section">
      <h2>Настройки</h2>
      <p className="lead">
        Наценка витрины и три уровня реферального кэшбэка. Уведомления о заказах уходят в Telegram, если
        заданы `TELEGRAM_BOT_TOKEN` и `ADMIN_TELEGRAM_CHAT_ID`.
      </p>
      <form className="checkout-form" onSubmit={onSave}>
        <label>
          Наценка, %
          <input value={markup} onChange={(e) => setMarkup(e.target.value)} type="number" min={0} max={100} step="0.1" />
        </label>
        <label>
          Округление до, ₽
          <input value={roundTo} onChange={(e) => setRoundTo(e.target.value)} type="number" min={1} />
        </label>
        <label>
          Рефералка L1, %
          <input value={l1} onChange={(e) => setL1(e.target.value)} type="number" min={0} max={50} step="0.1" />
        </label>
        <label>
          Рефералка L2, %
          <input value={l2} onChange={(e) => setL2(e.target.value)} type="number" min={0} max={50} step="0.1" />
        </label>
        <label>
          Рефералка L3, %
          <input value={l3} onChange={(e) => setL3(e.target.value)} type="number" min={0} max={50} step="0.1" />
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
