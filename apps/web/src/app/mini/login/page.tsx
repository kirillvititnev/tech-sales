"use client";

import { LoginForm } from "@/components/AuthForms";
import { useAuth } from "@/lib/auth";
import { AccountCabinet } from "@/components/AccountCabinet";

export default function MiniLoginPage() {
  const { me, ready } = useAuth();
  if (!ready) {
    return (
      <main className="section">
        <h2>Вход</h2>
        <p className="lead">Загрузка…</p>
      </main>
    );
  }
  if (me) {
    return (
      <AccountCabinet productBasePath="/mini/product" catalogHref="/mini" loginNext="/mini/account" />
    );
  }
  return (
    <main className="section">
      <h2>Вход</h2>
      <LoginForm nextHref="/mini/account" registerHref="/mini/register" />
    </main>
  );
}
