"use client";

import Link from "next/link";
import Image from "next/image";

import { useTelegramPrefill } from "@/lib/telegram";

export function MiniHeader() {
  const { inTelegram } = useTelegramPrefill();

  return (
    <header className="site-header mini-header">
      <Link href="/mini" className="brand">
        <Image src="/logo.png" alt="" width={36} height={36} priority aria-hidden />
        <span>White Shop</span>
      </Link>
      {inTelegram ? <span className="mini-badge">Telegram</span> : null}
    </header>
  );
}
