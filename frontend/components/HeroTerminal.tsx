import { CairnMark } from "./CairnMark";

const NAV = ["Overview", "Invoices", "Payments", "Team", "Settings"];

const ROWS = [
  { month: "September 2026", amount: "₹ 48,200", state: "due" },
  { month: "August 2026", amount: "₹ 46,900", state: "paid" },
  { month: "July 2026", amount: "₹ 51,400", state: "paid" },
];

/** A marker Cairn left on this exact control, so it never has to look for it again. */
function Marker({ className = "" }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={`grid h-[22px] w-[22px] shrink-0 place-items-center rounded-full bg-white text-moss ring-1 ring-moss/30 ${className}`}
    >
      <CairnMark className="h-[11px] w-[11px]" />
    </span>
  );
}

/** The hero shot: a real site, with Cairn's markers sitting on the controls it uses. */
export function HeroTerminal() {
  return (
    <div className="surface-floating overflow-hidden rounded-t-xl bg-white">
      {/* Cairn's own header — not browser chrome. Nobody browses with Cairn. */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-black/6 bg-soft px-5 py-3 sm:px-6">
        <span className="inline-flex items-center gap-2">
          <CairnMark className="h-[13px] w-[13px] text-ink/70" />
          <span className="font-mono text-[12.5px] text-ink">cairn</span>
        </span>
        <span className="font-mono text-[12.5px] text-faint">on</span>
        <span className="font-mono text-[12.5px] text-ink">billing.acme.com</span>
        <span className="ml-auto font-mono text-[12.5px] text-faint">
          driven by Claude Code
        </span>
      </div>

      {/* what Cairn did, stated once, calmly */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-black/6 bg-[#f4f8f5] px-5 py-3 sm:px-6">
        <span className="inline-flex items-center gap-2">
          <CairnMark className="h-[13px] w-[13px] text-moss" />
          <span className="font-mono text-[12.5px] text-moss">
            7 steps replayed from memory
          </span>
        </span>
        <span className="font-mono text-[12.5px] text-muted">0.4s</span>
        <span className="font-mono text-[12.5px] text-muted">1 tool call</span>
        <span className="font-mono text-[12.5px] text-muted">0 pages read</span>
      </div>

      {/* the site */}
      <div className="grid min-h-[360px] grid-cols-[176px_1fr] sm:grid-cols-[220px_1fr]">
        <aside className="border-r border-black/6 bg-soft px-4 py-6 sm:px-5">
          <p className="font-mono text-[11px] tracking-[0.06em] text-faint">ACME BILLING</p>
          <ul className="mt-5 space-y-1">
            {NAV.map((item) => (
              <li
                key={item}
                className={`flex items-center justify-between gap-2 rounded-sm py-2 pr-2 pl-3 text-[13px] ${
                  item === "Invoices"
                    ? "bg-white text-ink ring-1 ring-black/6"
                    : "text-muted"
                }`}
              >
                {item}
                {item === "Invoices" ? <Marker /> : null}
              </li>
            ))}
          </ul>
        </aside>

        <div className="px-5 py-6 sm:px-8 sm:py-7">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="mr-2 text-[16px] font-medium text-ink">Invoices</h3>
            <span className="inline-flex items-center gap-2 rounded-full bg-ink py-1 pr-1.5 pl-3.5 text-[12px] text-white">
              September
              <Marker />
            </span>
            {["August", "July"].map((month) => (
              <span
                key={month}
                className="rounded-full bg-black/4 px-3.5 py-1.5 text-[12px] text-muted"
              >
                {month}
              </span>
            ))}
          </div>

          <div className="well mt-5 rounded-md bg-white">
            {ROWS.map((row, i) => (
              <div
                key={row.month}
                className={`flex items-center justify-between gap-4 px-4 py-3.5 sm:px-5 ${
                  i === 0 ? "rounded-t-md bg-[#f4f8f5]" : "bg-white"
                } ${i === ROWS.length - 1 ? "rounded-b-md" : "border-b border-black/5"}`}
              >
                <span className="flex items-center gap-3">
                  {i === 0 ? (
                    <Marker />
                  ) : (
                    <span className="h-[22px] w-[22px] shrink-0 rounded-full bg-black/5" />
                  )}
                  <span className="text-[13.5px] text-ink">{row.month}</span>
                </span>
                <span className="flex items-center gap-4">
                  <span className="font-mono text-[13px] text-muted">{row.amount}</span>
                  <span
                    className={`rounded-full px-2.5 py-1 text-[11.5px] ${
                      row.state === "due"
                        ? "bg-[#f6ece2] text-[#a46a3c]"
                        : "bg-black/4 text-muted"
                    }`}
                  >
                    {row.state}
                  </span>
                </span>
              </div>
            ))}
          </div>

          <div className="mt-7 flex flex-wrap items-center gap-4">
            <span className="inline-flex items-center gap-2.5 rounded-sm bg-ink py-2 pr-2 pl-4 text-[13px] font-medium text-white">
              Get PDF
              <Marker />
            </span>
            <span className="font-mono text-[12.5px] text-faint">
              saved to ~/Downloads/acme-invoice-sep.pdf
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
