"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useCart } from "@/lib/cart";

const TABS = [
  { href: "/mini", label: "Каталог", match: (path: string) => path === "/mini" || path.startsWith("/mini/product") },
  { href: "/mini/hot", label: "HOT", match: (path: string) => path.startsWith("/mini/hot") },
  { href: "/mini/cart", label: "Корзина", match: (path: string) => path.startsWith("/mini/cart") || path.startsWith("/mini/checkout") || path.startsWith("/mini/order") },
];

export function MiniTabBar() {
  const pathname = usePathname() ?? "/mini";
  const { count, ready } = useCart();

  return (
    <nav className="mini-tabbar" aria-label="Основное меню">
      {TABS.map((tab) => {
        const current = tab.match(pathname);
        const cartLabel =
          tab.href === "/mini/cart" && ready && count > 0 ? `Корзина, ${count}` : tab.label;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={current ? "is-active" : undefined}
            aria-current={current ? "page" : undefined}
            aria-label={cartLabel}
          >
            <span>{tab.label}</span>
            {tab.href === "/mini/cart" && ready && count > 0 ? (
              <span className="mini-tabbar-count">{count}</span>
            ) : null}
          </Link>
        );
      })}
    </nav>
  );
}
