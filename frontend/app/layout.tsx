import type { Metadata } from "next";
import "@fontsource-variable/hanken-grotesk";
import "@fontsource-variable/shantell-sans";
import "lenis/dist/lenis.css";
import "./globals.css";
import { SmoothScroll } from "@/components/SmoothScroll";

const TAGLINE =
  "Your AI can use websites. But it forgets how, every single time. Cairn makes it remember.";

export const metadata: Metadata = {
  // Set NEXT_PUBLIC_SITE_URL at deploy time. Without a base, Next cannot turn the social
  // card images into absolute URLs, and every share falls back to localhost.
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: {
    default: "Cairn — a browser memory for AI agents",
    template: "%s · Cairn",
  },
  description: TAGLINE,
  openGraph: {
    title: "Cairn — a browser memory for AI agents",
    description: TAGLINE,
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Cairn — a browser memory for AI agents",
    description: TAGLINE,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <SmoothScroll>{children}</SmoothScroll>
      </body>
    </html>
  );
}
