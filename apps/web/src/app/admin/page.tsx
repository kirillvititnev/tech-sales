import { AdminOrdersTable } from "@/components/AdminOrdersTable";
import { api } from "@/lib/api";

export default async function AdminOrdersPage() {
  let orders: Awaited<ReturnType<typeof api.adminOrders>> = [];
  let error: string | null = null;
  try {
    orders = await api.adminOrders();
  } catch {
    error = "Не удалось загрузить заказы. Проверьте API.";
  }

  return (
    <main className="section">
      <h2>Заказы</h2>
      <p className="lead">
        Принят → оплачен → обработан → собран → отгружен. Оплата только через менеджера.
      </p>
      {error ? <p className="empty">{error}</p> : <AdminOrdersTable initialOrders={orders} />}
    </main>
  );
}
