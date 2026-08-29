"use client";

import { AccountCabinet } from "@/components/AccountCabinet";

export default function MiniAccountPage() {
  return (
    <AccountCabinet productBasePath="/mini/product" catalogHref="/mini" loginNext="/mini/account" />
  );
}
