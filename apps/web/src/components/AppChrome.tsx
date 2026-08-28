"use client";

import { usePathname } from "next/navigation";

import { SiteHeader } from "@/components/SiteHeader";
import { CartProvider } from "@/lib/cart";

export function AppChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isMini = pathname?.startsWith("/mini");
  return (
    <CartProvider>
      {isMini ? null : <SiteHeader />}
      {children}
    </CartProvider>
  );
}
