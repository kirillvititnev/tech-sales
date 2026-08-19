"use client";

import { useMemo, useState } from "react";

import { API_URL, formatPrice, type Order } from "@/lib/api";

const CUSTOMER_RU: Record<string, string> = {
  placed: "Оформлен",
  paid: "Оплачен",
  cancelled: "Отменён",
  ready: "Готов к выдаче",
  issued: "Выдан",
};

const ADMIN_RU: Record<string, string> = {
  accepted: "Принят",
  paid: "Оплачен",
  processing: "Обработан",
  assembled: "Собран",
  shipped: "Отгружен",
};

const ADMIN_FLOW = ["accepted", "paid", "processing", "assembled", "shipped"] as const;

function nextAdmin(status: string): string | null {
  const i = ADMIN_FLOW.indexOf(status as (typeof ADMIN_FLOW)[number]);
  if (i < 0 || i >= ADMIN_FLOW.length - 1) return null;
  return ADMIN_FLOW[i + 1];
}

export function AdminOrdersTable({ initialOrders }: { initialOrders: Order[] }) {
  const [orders, setOrders] = useState(initialOrders);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const sorted = useMemo(() => orders, [orders]);

  async function patchStatus(order: Order, admin_status: string) {
    setBusy(order.id);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/orders/${order.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ admin_status }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Ошибка смены статуса");
        return;
      }
      setOrders((prev) => prev.map((o) => (o.id === order.id ? { ...o, ...data } : o)));
    } catch {
      setError("Сеть недоступна");
    } finally {
      setBusy(null);
    }
  }

  async function runAction(order: Order, action: "issue" | "cancel") {
    setBusy(order.id);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/orders/${order.id}/actions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Ошибка действия");
        return;
      }
      setOrders((prev) => prev.map((o) => (o.id === order.id ? { ...o, ...data } : o)));
    } catch {
      setError("Сеть недоступна");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      {error ? <p className="form-error">{error}</p> : null}
      <table className="admin-table">
        <thead>
          <tr>
            <th>Номер</th>
            <th>Клиент</th>
            <th>Доставка</th>
            <th>Клиент</th>
            <th>Админ</th>
            <th>Сумма</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 ? (
            <tr>
              <td colSpan={7}>Заказов пока нет</td>
            </tr>
          ) : (
            sorted.map((o) => {
              const nxt = nextAdmin(o.admin_status);
              const disabled = busy === o.id || o.customer_status === "cancelled";
              return (
                <tr key={o.id}>
                  <td>{o.number}</td>
                  <td>
                    {o.customer_name}
                    <br />
                    <span style={{ color: "var(--mute)" }}>{o.customer_phone}</span>
                    {o.customer_telegram ? (
                      <>
                        <br />
                        <span style={{ color: "var(--mute)" }}>{o.customer_telegram}</span>
                      </>
                    ) : null}
                  </td>
                  <td>
                    {o.delivery_type === "cdek" ? "СДЭК" : "Москва"}
                    {o.delivery_address ? (
                      <>
                        <br />
                        <span style={{ color: "var(--mute)", fontSize: "0.85rem" }}>
                          {o.delivery_address}
                        </span>
                      </>
                    ) : null}
                  </td>
                  <td>{CUSTOMER_RU[o.customer_status] ?? o.customer_status}</td>
                  <td>{ADMIN_RU[o.admin_status] ?? o.admin_status}</td>
                  <td>{formatPrice(o.total_amount)}</td>
                  <td>
                    <div className="admin-actions">
                      {nxt ? (
                        <button
                          type="button"
                          className="btn btn-ghost admin-btn"
                          disabled={disabled}
                          onClick={() => patchStatus(o, nxt)}
                        >
                          → {ADMIN_RU[nxt]}
                        </button>
                      ) : null}
                      {o.customer_status === "ready" || o.customer_status === "paid" ? (
                        <button
                          type="button"
                          className="btn btn-ghost admin-btn"
                          disabled={disabled}
                          onClick={() => runAction(o, "issue")}
                        >
                          Выдан
                        </button>
                      ) : null}
                      {o.customer_status !== "cancelled" && o.customer_status !== "issued" ? (
                        <button
                          type="button"
                          className="btn btn-ghost admin-btn"
                          disabled={disabled}
                          onClick={() => runAction(o, "cancel")}
                        >
                          Отмена
                        </button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </>
  );
}
