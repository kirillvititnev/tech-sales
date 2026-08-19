import Link from "next/link";
import { notFound } from "next/navigation";

import { api, formatPrice } from "@/lib/api";

const STATUS_RU: Record<string, string> = {
  placed: "Оформлен",
  paid: "Оплачен",
  cancelled: "Отменён",
  ready: "Готов к выдаче",
  issued: "Выдан",
  accepted: "Принят",
  processing: "Обработан",
  assembled: "Собран",
  shipped: "Отгружен",
};

const DELIVERY_RU: Record<string, string> = {
  pickup_moscow: "Самовывоз, Москва",
  cdek: "СДЭК",
};

export default async function OrderPage({ params }: { params: Promise<{ number: string }> }) {
  const { number } = await params;
  let order: Awaited<ReturnType<typeof api.orderByNumber>>;
  try {
    order = await api.orderByNumber(number);
  } catch {
    notFound();
  }

  return (
    <main className="section">
      <p className="product-brand">Заказ принят</p>
      <h2>{order.number}</h2>
      <p className="lead">
        Менеджер свяжется с вами для подтверждения и оплаты. Онлайн-оплаты нет.
      </p>
      <dl className="order-meta">
        <div>
          <dt>Статус</dt>
          <dd>{STATUS_RU[order.customer_status] ?? order.customer_status}</dd>
        </div>
        <div>
          <dt>Доставка</dt>
          <dd>{DELIVERY_RU[order.delivery_type] ?? order.delivery_type}</dd>
        </div>
        {order.delivery_address ? (
          <div>
            <dt>Адрес</dt>
            <dd>{order.delivery_address}</dd>
          </div>
        ) : null}
        <div>
          <dt>Сумма</dt>
          <dd>{formatPrice(order.total_amount)}</dd>
        </div>
        <div>
          <dt>Контакт</dt>
          <dd>
            {order.customer_name}, {order.customer_phone}
            {order.customer_telegram ? ` · ${order.customer_telegram}` : ""}
          </dd>
        </div>
      </dl>
      <ul className="order-items">
        {order.items?.map((item) => (
          <li key={item.id}>
            {item.title} × {item.quantity} — {formatPrice(String(item.unit_price))}
          </li>
        ))}
      </ul>
      <div className="cta-row">
        <Link href="/#catalog" className="btn btn-primary">
          В каталог
        </Link>
      </div>
    </main>
  );
}
