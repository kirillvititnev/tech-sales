"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useCart } from "@/lib/cart";

export function CartNavLink({ href = "/cart" }: { href?: string }) {
  const { count, ready } = useCart();
  const pathname = usePathname() ?? "";
  const current =
    pathname === href ||
    pathname.startsWith("/cart") ||
    pathname.startsWith("/checkout") ||
    pathname.startsWith("/order");

  return (
    <Link href={href} aria-current={current && href === "/cart" ? "page" : undefined}>
      Корзина{ready && count > 0 ? ` (${count})` : ""}
    </Link>
  );
}
