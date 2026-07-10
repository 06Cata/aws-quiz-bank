import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AWS Quiz Bank",
  description: "AWS Cloud Practitioner bilingual quiz practice"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-Hant">
      <body>{children}</body>
    </html>
  );
}
