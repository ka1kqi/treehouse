import type { Metadata, Viewport } from "next";
import { JetBrains_Mono } from "next/font/google";
import "./globals.css";

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
  weight: ["300", "400", "500"],
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL
  ? process.env.NEXT_PUBLIC_SITE_URL
  : process.env.VERCEL_URL
    ? `https://${process.env.VERCEL_URL}`
    : "http://localhost:3001";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: "Treehouse — Parallel runtime isolation for multi-agent coding",
  description:
    "A CLI that spawns isolated worktrees, Docker projects, and environments per AI agent — then merges them back with AI-assisted conflict resolution.",
  openGraph: {
    title: "Treehouse — Parallel runtime isolation for multi-agent coding",
    description:
      "Parallel runtime isolation for multi-agent coding. A CLI harness plus per-agent sandboxes.",
    type: "website",
    siteName: "Treehouse",
  },
  twitter: {
    card: "summary_large_image",
    title: "Treehouse — Parallel runtime isolation for multi-agent coding",
    description:
      "Parallel runtime isolation for multi-agent coding. A CLI harness plus per-agent sandboxes.",
  },
};

export const viewport: Viewport = {
  themeColor: "#0a0a0a",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={mono.variable}>
      <body className="bg-bg text-fg font-mono antialiased">{children}</body>
    </html>
  );
}
