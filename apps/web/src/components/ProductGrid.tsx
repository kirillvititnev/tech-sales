"use client";

import Link from "next/link";
import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type PointerEvent,
} from "react";
import { createPortal } from "react-dom";

import { AddToCartButton } from "@/components/AddToCartButton";
import { formatPrice, type Product } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export function formatDeviceCategory(category: string) {
  if (category === "Asis+*" || category === "Смартфоны ASIS+") return "Смартфоны ASIS+";
  if (category === "Asis*" || category === "Смартфоны ASIS") return "Смартфоны ASIS";
  return category;
}

export function catalogParts(p: Product) {
  const a = p.attributes ?? {};
  const category = formatDeviceCategory(
    typeof a.device_category === "string" ? a.device_category : "",
  );
  const deviceName = typeof a.device_name === "string" ? a.device_name : "";
  const storage = typeof a.storage === "string" ? a.storage : "";
  const ram = typeof a.ram === "string" ? a.ram : "";
  const color = typeof a.color === "string" ? a.color : "";
  const sim = typeof a.sim === "string" ? a.sim : "";
  const band = typeof a.band === "string" ? a.band : "";
  const config = typeof a.config === "string" ? a.config : "";

  const mem =
    ram && storage
      ? `${ram.replace(/GB$/i, "")}/${storage}`
      : storage || ram || "";
  const headlineBits = [deviceName || p.title, mem, color, sim || band].filter(Boolean);
  const name = deviceName ? headlineBits.join(" · ") : p.title;

  const subtitleParts = config
    .split(" · ")
    .map((x) => x.trim())
    .filter(Boolean)
    .filter((part) => {
      const lower = part.toLowerCase();
      if (mem && lower === mem.toLowerCase()) return false;
      if (storage && lower === storage.toLowerCase()) return false;
      if (color && lower === color.toLowerCase()) return false;
      if (sim && lower === sim.toLowerCase()) return false;
      if (band && lower === band.toLowerCase()) return false;
      return true;
    });

  return {
    brand: p.brand ?? "—",
    category,
    name,
    config: subtitleParts.join(" · "),
  };
}

export function ProductGrid({
  products,
  productBasePath = "/product",
  emptyHref,
  emptyLabel = "К каталогу",
  emptyText = "Пока нет товаров на витрине.",
}: {
  products: Product[];
  productBasePath?: string;
  emptyHref?: string;
  emptyLabel?: string;
  emptyText?: string;
}) {
  const cartHref = productBasePath.startsWith("/mini") ? "/mini/cart" : "/cart";
  const loginHref = productBasePath.startsWith("/mini") ? "/mini/account" : "/login";
  const [open, setOpen] = useState<Product | null>(null);
  const [closing, setClosing] = useState(false);
  const openerRef = useRef<HTMLButtonElement | null>(null);

  const closeSheet = useCallback(() => {
    setClosing(true);
  }, []);

  const finishClose = useCallback(() => {
    setOpen(null);
    setClosing(false);
    requestAnimationFrame(() => openerRef.current?.focus());
  }, []);

  if (!products.length) {
    return (
      <div className="empty-state">
        <p className="empty">{emptyText}</p>
        {emptyHref ? (
          <Link href={emptyHref} className="btn btn-primary">
            {emptyLabel}
          </Link>
        ) : null}
      </div>
    );
  }

  return (
    <>
      <div className="product-grid">
        {products.map((p) => {
          const { brand, category, name, config } = catalogParts(p);
          const expanded = open?.id === p.id;
          return (
            <button
              key={p.id}
              type="button"
              className="product-row"
              aria-expanded={expanded}
              aria-haspopup="dialog"
              onClick={(e) => {
                openerRef.current = e.currentTarget;
                setClosing(false);
                setOpen(p);
              }}
            >
              <span className="product-copy">
                <span className="product-brand">{brand}</span>
                {category ? <span className="product-category">{category}</span> : null}
                <span className="product-row-title">{name}</span>
                {config ? <span className="product-config">{config}</span> : null}
              </span>
              <span className="product-meta">
                {p.is_hot ? <span className="hot-tag">HOT</span> : null}
                <strong>{formatPrice(p.price)}</strong>
              </span>
            </button>
          );
        })}
      </div>
      {open ? (
        <ProductSheet
          product={open}
          cartHref={cartHref}
          loginHref={loginHref}
          closing={closing}
          onClose={closeSheet}
          onExited={finishClose}
        />
      ) : null}
    </>
  );
}

function ProductSheet({
  product,
  cartHref,
  loginHref,
  closing,
  onClose,
  onExited,
}: {
  product: Product;
  cartHref: string;
  loginHref: string;
  closing: boolean;
  onClose: () => void;
  onExited: () => void;
}) {
  const titleId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);
  const sheetRef = useRef<HTMLDivElement>(null);
  const dragStartY = useRef<number | null>(null);
  const [dragY, setDragY] = useState(0);
  const [entered, setEntered] = useState(false);
  const { me, favoriteIds, toggleFavorite, recordView } = useAuth();
  const { brand, category, name, config } = catalogParts(product);
  const note =
    typeof product.description === "string" && product.description.trim()
      ? product.description
      : "Менеджер подтвердит заказ и оплату лично.";

  useEffect(() => {
    if (!closing) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const ms = reduce ? 0 : 340;
    const timer = window.setTimeout(onExited, ms);
    return () => window.clearTimeout(timer);
  }, [closing, onExited]);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const ms = reduce ? 0 : 450;
    const timer = window.setTimeout(() => setEntered(true), ms);
    return () => window.clearTimeout(timer);
  }, [product.id]);

  useEffect(() => {
    recordView(product.id);
  }, [product.id, recordView]);

  useEffect(() => {
    const sheet = sheetRef.current;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();

    function focusables() {
      if (!sheet) return [];
      return [...sheet.querySelectorAll<HTMLElement>("button, a[href], input, select, textarea")].filter(
        (el) => !el.hasAttribute("disabled") && el.getAttribute("aria-hidden") !== "true",
      );
    }

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key !== "Tab") return;
      const items = focusables();
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prevOverflow;
      document.removeEventListener("keydown", onKey);
    };
  }, [onClose, product.id]);

  function isDesktop() {
    return window.matchMedia("(min-width: 721px)").matches;
  }

  function onHandlePointerDown(e: PointerEvent<HTMLDivElement>) {
    if (isDesktop()) return;
    dragStartY.current = e.clientY;
    e.currentTarget.setPointerCapture(e.pointerId);
  }

  function onHandlePointerMove(e: PointerEvent<HTMLDivElement>) {
    if (dragStartY.current == null) return;
    const next = Math.max(0, e.clientY - dragStartY.current);
    setDragY(next);
  }

  function onHandlePointerUp() {
    if (dragStartY.current == null) return;
    if (dragY > 80) onClose();
    else setDragY(0);
    dragStartY.current = null;
  }

  return createPortal(
    <div className={closing ? "product-sheet-root is-closing" : "product-sheet-root"}>
      <div className="product-sheet-backdrop" onClick={onClose} />
      <div
        ref={sheetRef}
        className={[
          "product-sheet",
          dragY ? "is-dragging" : "",
          entered ? "has-entered" : "",
        ]
          .filter(Boolean)
          .join(" ")}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        style={dragY ? { transform: `translateY(${dragY}px)` } : undefined}
      >
        <div
          className="product-sheet-handle"
          aria-hidden="true"
          onPointerDown={onHandlePointerDown}
          onPointerMove={onHandlePointerMove}
          onPointerUp={onHandlePointerUp}
          onPointerCancel={onHandlePointerUp}
        />
        <div className="product-sheet-top">
          <p className="product-brand">{brand}</p>
          <button
            ref={closeRef}
            type="button"
            className="product-sheet-close"
            onClick={onClose}
          >
            Закрыть
          </button>
        </div>
        {category ? <p className="product-category">{category}</p> : null}
        <p id={titleId} className="product-sheet-title">
          {name}
        </p>
        {config ? <p className="product-config">{config}</p> : null}
        <p className="product-sheet-note">{note}</p>
        <p className="product-sheet-price">
          <strong>{formatPrice(product.price)}</strong>
        </p>
        {me ? (
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => {
              void toggleFavorite(product.id);
            }}
          >
            {favoriteIds.has(product.id) ? "В избранном" : "В избранное"}
          </button>
        ) : (
          <Link href={loginHref} className="btn btn-ghost">
            В избранное — войдите
          </Link>
        )}
        <AddToCartButton key={product.id} product={product} cartHref={cartHref} />
      </div>
    </div>,
    document.body,
  );
}
