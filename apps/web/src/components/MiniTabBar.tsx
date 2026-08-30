"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useCart } from "@/lib/cart";
import { useAuth } from "@/lib/auth";

const TABS = [
  { href: "/mini", label: "Каталог", match: (path: string) => path === "/mini" || path.startsWith("/mini/product") },
  { href: "/mini/hot", label: "HOT", match: (path: string) => path.startsWith("/mini/hot") },
  { href: "/mini/cart", label: "Корзина", match: (path: string) => path.startsWith("/mini/cart") || path.startsWith("/mini/checkout") || path.startsWith("/mini/order") },
  { href: "/mini/account", label: "Кабинет", match: (path: string) => path.startsWith("/mini/account") || path.startsWith("/mini/login") || path.startsWith("/mini/register") },
];

export function MiniTabBar() {
  const pathname = usePathname() ?? "/mini";
  const { count, ready } = useCart();
  const { me, unreadCount } = useAuth();

  return (
    <nav className="mini-tabbar" aria-label="Основное меню">
      {TABS.map((tab) => {
        const current = tab.match(pathname);
        const cartLabel =
          tab.href === "/mini/cart" && ready && count > 0 ? `Корзина, ${count}` : tab.label;
        const accountLabel =
          tab.href === "/mini/account" && me && unreadCount > 0
            ? `Кабинет, непрочитанных ${unreadCount}`
            : tab.label;
        const ariaLabel = tab.href === "/mini/account" ? accountLabel : cartLabel;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={current ? "is-active" : undefined}
            aria-current={current ? "page" : undefined}
            aria-label={ariaLabel}
          >
            <span>{tab.label}</span>
            {tab.href === "/mini/cart" && ready && count > 0 ? (
              <span className="nav-count" aria-hidden="true">
                {count}
              </span>
            ) : null}
            {tab.href === "/mini/account" && me && unreadCount > 0 ? (
              <span className="nav-count" aria-hidden="true">
                {unreadCount > 99 ? "99+" : unreadCount}
              </span>
            ) : null}
          </Link>
        );
      })}
    </nav>
  );
}
