"use client";

import { usePathname } from "next/navigation";

import { SiteHeader } from "@/components/SiteHeader";

export function AppChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isMini = pathname?.startsWith("/mini");
  return (
    <>
      {isMini ? null : <SiteHeader />}
      {children}
    </>
  );
}
