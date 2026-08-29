"use client";

import { AccountCabinet } from "@/components/AccountCabinet";
import { LoginForm } from "@/components/AuthForms";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { me, ready } = useAuth();

  if (!ready) {
    return (
      <main className="section">
        <h2>Вход</h2>
        <p className="lead">Загрузка…</p>
      </main>
    );
  }
  if (me) return <AccountCabinet />;

  return (
    <main className="section">
      <h2>Вход</h2>
      <p className="lead">Telegram Login или email и пароль.</p>
      <LoginForm nextHref="/account" registerHref="/register" />
    </main>
  );
}
