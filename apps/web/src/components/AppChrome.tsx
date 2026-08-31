"use client";

import { usePathname } from "next/navigation";

import { SiteHeader } from "@/components/SiteHeader";
import { AuthProvider } from "@/lib/auth";
import { CartProvider } from "@/lib/cart";

export function AppChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isMini = pathname?.startsWith("/mini");
  return (
    <AuthProvider>
      <CartProvider>
        {isMini ? null : <SiteHeader />}
        {children}
      </CartProvider>
    </AuthProvider>
  );
}
