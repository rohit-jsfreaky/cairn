import { CairnMark } from "./CairnMark";
import { Container } from "./Container";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { href: "#what", label: "What it does" },
      { href: "#speed", label: "Why it is fast" },
      { href: "#install", label: "Install" },
    ],
  },
  {
    title: "Works with",
    links: [
      { href: "#install", label: "Claude Code" },
      { href: "#install", label: "Cursor" },
      { href: "#install", label: "Codex" },
    ],
  },
  {
    title: "Project",
    links: [
      { href: "#install", label: "GitHub" },
      { href: "#install", label: "Prior work" },
      { href: "#install", label: "License" },
    ],
  },
];

export function SiteFooter() {
  return (
    <footer className="bg-white py-20">
      <Container>
        <div className="grid gap-12 sm:grid-cols-2 lg:grid-cols-4">
          <div className="flex items-center gap-2.5 text-ink">
            <CairnMark className="h-[19px] w-[19px]" />
            <span className="font-display text-[18px] font-medium">Cairn</span>
          </div>

          {COLUMNS.map((column) => (
            <div key={column.title}>
              <p className="text-[14px] text-faint">{column.title}</p>
              <ul className="mt-5 space-y-3.5">
                {column.links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="text-[15px] text-ink/75 transition-colors hover:text-ink"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-16 flex flex-col gap-2 pt-7 text-[14px] text-faint sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 Cairn</p>
          <p>A cairn marks the way, so the next traveller does not have to look for it.</p>
        </div>
      </Container>
    </footer>
  );
}
