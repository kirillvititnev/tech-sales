"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { CartNavLink } from "@/components/CartNavLink";
import { useAuth } from "@/lib/auth";

export function SiteHeader() {
  const pathname = usePathname() ?? "/";
  const { me, ready, unreadCount } = useAuth();
  const accountCurrent =
    pathname.startsWith("/account") || pathname.startsWith("/login") || pathname.startsWith("/register");

  return (
    <header className="site-header">
      <Link href="/" className="brand" aria-current={pathname === "/" ? "page" : undefined}>
        <Image src="/logo.png" alt="" width={40} height={40} priority aria-hidden />
        <span>White Shop</span>
      </Link>
      <nav aria-label="Основное меню">
        <Link href="/hot" aria-current={pathname.startsWith("/hot") ? "page" : undefined}>
          HOT
        </Link>
        <Link
          href="/catalog"
          aria-current={pathname.startsWith("/catalog") || pathname.startsWith("/product") ? "page" : undefined}
        >
          Каталог
        </Link>
        <CartNavLink href="/cart" />
        {ready && me ? (
          <Link
            href="/account"
            aria-current={accountCurrent ? "page" : undefined}
            aria-label={unreadCount > 0 ? `Кабинет, непрочитанных ${unreadCount}` : "Кабинет"}
          >
            <span>Кабинет</span>
            {unreadCount > 0 ? (
              <span className="nav-count" aria-hidden="true">
                {unreadCount > 99 ? "99+" : unreadCount}
              </span>
            ) : null}
          </Link>
        ) : (
          <Link href="/login" aria-current={accountCurrent ? "page" : undefined}>
            Войти
          </Link>
        )}
      </nav>
    </header>
  );
}
