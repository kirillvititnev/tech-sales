"use client";

import { AccountCabinet } from "@/components/AccountCabinet";
import { RegisterForm } from "@/components/AuthForms";
import { useAuth } from "@/lib/auth";

export default function MiniRegisterPage() {
  const { me, ready } = useAuth();
  if (!ready) {
    return (
      <main className="section">
        <h2>Регистрация</h2>
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
      <h2>Регистрация</h2>
      <RegisterForm nextHref="/mini/account" loginHref="/mini/login" />
    </main>
  );
}
