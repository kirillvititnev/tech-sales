import { api } from "@/lib/api";

export default async function AdminPage() {
  let orders: Awaited<ReturnType<typeof api.adminOrders>> = [];
  let error: string | null = null;

  try {
    orders = await api.adminOrders();
  } catch {
    error = "Не удалось загрузить заказы. Проверьте API.";
  }

  return (
    <main className="section">
      <h2>Админка</h2>
      <p className="lead">Заказы, каналы и модерация — каркас первой версии.</p>
      {error ? <p className="empty">{error}</p> : null}
      <table className="admin-table">
        <thead>
          <tr>
            <th>Номер</th>
            <th>Клиент</th>
            <th>Клиент-статус</th>
            <th>Админ-статус</th>
            <th>Сумма</th>
          </tr>
        </thead>
        <tbody>
          {orders.length === 0 ? (
            <tr>
              <td colSpan={5}>Заказов пока нет</td>
            </tr>
          ) : (
            orders.map((o) => (
              <tr key={o.id}>
                <td>{o.number}</td>
                <td>
                  {o.customer_name}
                  <br />
                  <span style={{ color: "var(--mute)" }}>{o.customer_phone}</span>
                </td>
                <td>{o.customer_status}</td>
                <td>{o.admin_status}</td>
                <td>{o.total_amount} ₽</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </main>
  );
}
