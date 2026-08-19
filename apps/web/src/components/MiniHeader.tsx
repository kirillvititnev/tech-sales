"use client";

import Link from "next/link";
import Image from "next/image";

import { useTelegramPrefill } from "@/lib/telegram";

export function MiniHeader() {
  const { inTelegram } = useTelegramPrefill();

  return (
    <header className="site-header mini-header">
      <Link href="/mini" className="brand">
        <Image src="/logo.png" alt="White Shop" width={36} height={36} priority />
        <span>White Shop</span>
      </Link>
      <nav>
        <Link href="/mini">Каталог</Link>
        <Link href="/mini/hot">HOT</Link>
        {inTelegram ? <span className="mini-badge">Telegram</span> : null}
      </nav>
    </header>
  );
}
