import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Ho smartvision — Panel de Técnicos",
  description: "Gestión de cámaras CCTV: clientes, propiedades y ONVIF.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
