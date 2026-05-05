import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MiamDelivery",
  description: "Commande de repas connectee a l'API Restaurant",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
