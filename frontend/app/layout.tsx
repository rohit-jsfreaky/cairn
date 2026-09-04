import type { Metadata } from "next";
import "@fontsource-variable/hanken-grotesk";
import "@fontsource-variable/shantell-sans";
import "lenis/dist/lenis.css";
import "./globals.css";
import { SmoothScroll } from "@/components/SmoothScroll";

const TAGLINE =
  "Your AI can use websites. But it forgets how, every single time. Cairn makes it remember.";

const TITLE = "Cairn — a browser memory for AI agents";

// The real home, and the DEFAULT rather than a fallback to localhost. Next needs an
// absolute base to turn the social card into a shareable URL, and a deploy that forgot to
// set an environment variable used to publish `http://localhost:3000/opengraph-image` —
// a link that is broken everywhere except the machine that built it.
// NEXT_PUBLIC_SITE_URL still wins, so a preview deployment can point at itself.
export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://cairnmcp.fun";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: TITLE, template: "%s · Cairn" },
  description: TAGLINE,
  applicationName: "Cairn",
  alternates: { canonical: "/" },
  openGraph: {
    title: TITLE,
    description: TAGLINE,
    type: "website",
    url: SITE_URL,
    siteName: "Cairn",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
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
