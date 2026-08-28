"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { CartNavLink } from "@/components/CartNavLink";

export function SiteHeader() {
  const pathname = usePathname() ?? "/";

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
      </nav>
    </header>
  );
}
