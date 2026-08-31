"use client";

import { useId } from "react";
import { createPortal } from "react-dom";

import { formatPrice } from "@/lib/api";
import type { CartPendingChange } from "@/lib/cartPrices";

export function CartPriceSheet({
  pending,
  onAccept,
  onRemove,
}: {
  pending: CartPendingChange[];
  onAccept: () => void;
  onRemove: (productId: string) => void;
}) {
  const titleId = useId();
  if (typeof document === "undefined" || pending.length === 0) return null;

  return createPortal(
    <div className="product-sheet-root">
      <div className="product-sheet-backdrop" />
      <div className="product-sheet has-entered" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <div className="product-sheet-handle" aria-hidden="true" />
        <p className="product-brand">Котировка витрины</p>
        <h2 id={titleId} className="product-sheet-title">
          Цена изменилась
        </h2>
        <p className="product-sheet-note">
          Число на карточке — котировка. Менеджер подтвердит сумму и примет оплату. Снижение уже
          применено. Рост цены и снятие с витрины — только с вашего согласия.
        </p>
        <ul className="cart-pending-list">
          {pending.map((item) => (
            <li key={item.productId} className="cart-pending-item">
              <div>
                <strong>{item.title}</strong>
                <p className="account-note">
                  {item.kind === "removed"
                    ? "снят с витрины"
                    : `было ${formatPrice(item.oldPrice)} · стало ${formatPrice(item.newPrice)}`}
                </p>
              </div>
              <button
                type="button"
                className="btn btn-ghost admin-btn"
                onClick={() => onRemove(item.productId)}
              >
                Убрать
              </button>
            </li>
          ))}
        </ul>
        <div className="cta-row">
          <button type="button" className="btn btn-primary" onClick={onAccept} autoFocus>
            Продолжить
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
