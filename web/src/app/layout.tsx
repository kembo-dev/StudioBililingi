import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "StudioBililingi",
  description: "Studio de production de séries IA",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
