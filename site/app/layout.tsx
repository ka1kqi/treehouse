import type { Metadata, Viewport } from "next";
import { JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { getSiteUrl } from "./site-url";

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
  weight: ["300", "400", "500"],
});

const siteUrl = getSiteUrl();

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: "Treehouse — Parallel runtime isolation for multi-agent coding",
  description:
    "An orchestrator decomposes a task into parallel agents, each in an isolated worktree and Docker project — then merges their work back with AI-assisted conflict resolution.",
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
