import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OFFAIR AI | Secure Offline AI",
  description: "Secure offline AI for company documents and PDFs.",
  icons: {
    icon: [{ url: "/favicon.png?v=2", type: "image/png" }],
    shortcut: ["/favicon.png?v=2"],
    apple: [{ url: "/favicon.png?v=2", type: "image/png" }],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" type="image/png" href="/favicon.png?v=2" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@500;600;700&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body style={{ height: "100vh", overflow: "hidden" }}>{children}</body>
    </html>
  );
}
