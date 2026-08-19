import { AdminOrdersTable } from "@/components/AdminOrdersTable";
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
      <h2>Админка · заказы</h2>
      <p className="lead">
        Статусы: принят → оплачен → обработан → собран → отгружен. Клиенту зеркалятся оплата / готов /
        выдан. Оплата только через менеджера.
      </p>
      {error ? <p className="empty">{error}</p> : <AdminOrdersTable initialOrders={orders} />}
    </main>
  );
}
