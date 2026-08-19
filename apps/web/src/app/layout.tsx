import type { Metadata } from "next";
import { Manrope, Oswald } from "next/font/google";

import { SiteHeader } from "@/components/SiteHeader";

import "./globals.css";

const body = Manrope({
  variable: "--font-body",
  subsets: ["latin", "cyrillic"],
});

const display = Oswald({
  variable: "--font-display",
  subsets: ["latin", "cyrillic"],
});

export const metadata: Metadata = {
  title: "White Shop",
  description: "Техника с умной витриной цен",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body className={`${body.variable} ${display.variable} antialiased`}>
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
