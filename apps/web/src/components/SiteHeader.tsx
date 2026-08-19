import Image from "next/image";
import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="site-header">
      <Link href="/" className="brand">
        <Image src="/logo.png" alt="White Shop" width={40} height={40} priority />
        <span>White Shop</span>
      </Link>
      <nav>
        <Link href="/hot">HOT</Link>
        <Link href="/#catalog">Каталог</Link>
        <Link href="/mini">Mini App</Link>
        <Link href="/admin">Админка</Link>
      </nav>
    </header>
  );
}
