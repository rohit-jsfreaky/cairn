import Link from "next/link";
import { CairnMark } from "./CairnMark";

const LINKS = [
  { href: "#what", label: "What it does" },
  { href: "#speed", label: "Why it is fast" },
  { href: "#install", label: "Install" },
];

export function SiteNav() {
  return (
    <header className="flex items-center justify-between px-6 pt-6 sm:px-10">
      <Link href="/" className="flex items-center gap-2.5 text-ink">
        <CairnMark className="h-[19px] w-[19px]" />
        <span className="font-display text-[18px] font-medium">Cairn</span>
      </Link>

      <nav className="hidden items-center gap-9 md:flex">
        {LINKS.map((link) => (
          <a
            key={link.href}
            href={link.href}
            className="text-[14px] font-medium text-ink/70 transition-colors hover:text-ink"
          >
            {link.label}
          </a>
        ))}
      </nav>

      <a
        href="#install"
        className="rounded-full bg-ink px-5 py-2.5 text-[14px] font-medium text-white transition-opacity hover:opacity-85"
      >
        Install Cairn
      </a>
    </header>
  );
}
