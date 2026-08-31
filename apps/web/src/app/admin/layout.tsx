import Link from "next/link";

const LINKS = [
  { href: "/admin", label: "Заказы" },
  { href: "/admin/users", label: "Пользователи" },
  { href: "/admin/channels", label: "Каналы" },
  { href: "/admin/catalog", label: "Каталог" },
  { href: "/admin/settings", label: "Настройки" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="admin-shell">
      <nav className="admin-nav">
        {LINKS.map((l) => (
          <Link key={l.href} href={l.href}>
            {l.label}
          </Link>
        ))}
      </nav>
      {children}
    </div>
  );
}
