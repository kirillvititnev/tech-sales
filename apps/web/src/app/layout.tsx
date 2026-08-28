import type { Metadata, Viewport } from "next";
import { Manrope, Oswald } from "next/font/google";

import { AppChrome } from "@/components/AppChrome";

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

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  colorScheme: "light dark",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body className={`${body.variable} ${display.variable} antialiased`}>
        <AppChrome>{children}</AppChrome>
      </body>
    </html>
  );
}
