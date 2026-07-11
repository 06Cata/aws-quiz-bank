import type { Metadata } from "next";
import type { Viewport } from "next";
import { PwaRegister } from "@/components/PwaRegister";
import "./globals.css";

export const metadata: Metadata = {
  title: "AWS Quiz Bank",
  description: "AWS Cloud Practitioner bilingual quiz practice",
  manifest: "/manifest.webmanifest",
  applicationName: "AWS Quiz Bank",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "AWS Quiz Bank"
  },
  icons: {
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
      { url: "/icons/icon.svg", type: "image/svg+xml" }
    ],
    apple: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" }
    ]
  }
};

export const viewport: Viewport = {
  themeColor: "#000000",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-Hant">
      <body>
        {children}
        <PwaRegister />
      </body>
    </html>
  );
}
