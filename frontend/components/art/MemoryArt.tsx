"use client";

import { useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import { CairnMark } from "../CairnMark";

gsap.registerPlugin(useGSAP, ScrollTrigger);

const ROWS = [
  { site: "billing.acme.com", steps: 7, walked: 41, used: "today, 09:14" },
  { site: "dash.internal.io", steps: 11, walked: 130, used: "yesterday, 18:02" },
  { site: "portal.gst.gov.in", steps: 9, walked: 12, used: "3 days ago" },
  { site: "admin.shopify.com", steps: 6, walked: 27, used: "last week" },
  { site: "reports.stripe.com", steps: 8, walked: 19, used: "last week" },
];

/** What Cairn is holding on this machine right now. */
export function MemoryArt() {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      gsap.from("[data-row]", {
        opacity: 0,
        y: 16,
        duration: 0.6,
        ease: "power3.out",
        stagger: 0.09,
        scrollTrigger: { trigger: root.current, start: "top 85%", once: true },
      });

      gsap.from("[data-dot]", {
        scale: 0,
        transformOrigin: "center",
        duration: 0.35,
        ease: "back.out(2.4)",
        stagger: 0.012,
        scrollTrigger: { trigger: root.current, start: "top 85%", once: true },
      });
    },
    { scope: root },
  );

  return (
    <div
      ref={root}
      className="surface-floating overflow-hidden rounded-t-xl bg-white"
    >
      <div className="flex flex-wrap items-center gap-3 border-b border-black/6 bg-soft px-5 py-3.5 sm:px-6">
        <CairnMark className="h-[13px] w-[13px] text-ink/70" />
        <span className="font-mono text-[12.5px] text-ink">cairn memory</span>
        <span className="rounded-full bg-white px-2.5 py-1 font-mono text-[11.5px] text-muted ring-1 ring-black/6">
          5 sites
        </span>
        <span className="ml-auto font-mono text-[12px] text-faint">
          ~/.sibyl-memory/memory.db
        </span>
      </div>

      <div className="grid grid-cols-[1fr_84px_120px] gap-4 border-b border-black/6 px-5 py-3 font-mono text-[11.5px] tracking-[0.04em] text-faint sm:grid-cols-[1fr_150px_110px_150px] sm:px-6">
        <span>SITE</span>
        <span className="hidden sm:block">TRAIL</span>
        <span>WALKED</span>
        <span>LAST</span>
      </div>

      {ROWS.map((row) => (
        <div
          key={row.site}
          data-row
          className="grid grid-cols-[1fr_84px_120px] items-center gap-4 border-b border-black/5 px-5 py-4 last:border-b-0 sm:grid-cols-[1fr_150px_110px_150px] sm:px-6"
        >
          <span className="flex min-w-0 items-center gap-3">
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-sm bg-black/5 font-mono text-[11px] text-muted">
              {row.site[0]}
            </span>
            <span className="truncate font-mono text-[13.5px] text-ink">{row.site}</span>
          </span>

          <span className="hidden items-center gap-1 sm:flex">
            {Array.from({ length: row.steps }).map((_, i) => (
              <span
                key={i}
                data-dot
                className="h-[7px] w-[7px] rounded-full bg-moss/45"
              />
            ))}
          </span>

          <span className="font-mono text-[13px] text-muted">{row.walked}×</span>
          <span className="truncate font-mono text-[13px] text-faint">{row.used}</span>
        </div>
      ))}
    </div>
  );
}
