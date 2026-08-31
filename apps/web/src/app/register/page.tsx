"use client";

import { AccountCabinet } from "@/components/AccountCabinet";
import { RegisterForm } from "@/components/AuthForms";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const { me, ready } = useAuth();

  if (!ready) {
    return (
      <main className="section">
        <h2>Регистрация</h2>
        <p className="lead">Загрузка…</p>
      </main>
    );
  }
  if (me) return <AccountCabinet />;

  return (
    <main className="section">
      <h2>Регистрация</h2>
      <p className="lead">Email и пароль или Telegram. Реферальный код из ссылки подставится сам.</p>
      <RegisterForm nextHref="/account" loginHref="/login" />
    </main>
  );
}
