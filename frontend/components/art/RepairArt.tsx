"use client";

import { useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { DrawSVGPlugin } from "gsap/DrawSVGPlugin";
import { useGSAP } from "@gsap/react";
import { ArtCard } from "./ArtCard";
import { Blob } from "./Blob";
import { Check, Cross } from "./Glyphs";
import { Panel } from "./Panel";

gsap.registerPlugin(useGSAP, ScrollTrigger, DrawSVGPlugin);

export function RepairArt() {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const tl = gsap.timeline({
        scrollTrigger: { trigger: root.current, start: "top 78%", once: true },
      });

      tl.from("[data-old]", { opacity: 0, x: -8, duration: 0.5, ease: "power2.out" })
        .from(
          "[data-strike]",
          { scaleX: 0, transformOrigin: "left center", duration: 0.55, ease: "power2.inOut" },
          "+=0.35",
        )
        .from(
          "[data-new]",
          { opacity: 0, y: 14, duration: 0.6, ease: "power3.out" },
          "-=0.15",
        )
        .from(
          "[data-hop]",
          { drawSVG: "0%", duration: 0.7, ease: "power2.inOut" },
          "-=0.55",
        )
        .from(
          "[data-saved]",
          { opacity: 0, duration: 0.5, ease: "power2.out" },
          "-=0.2",
        );
    },
    { scope: root },
  );

  return (
    <div ref={root}>
      <ArtCard>
        <Blob className="-left-20 -top-16 h-[80%] w-[80%]" color="#eec3b2" />
        <Blob className="-right-20 bottom-[-8%] h-[65%] w-[70%]" color="#f6ddd2" />

        <Panel
          title="step 5  ·  the page did not change"
          className="absolute left-[9%] top-[15%] w-[106%]"
        >
          <div className="relative px-5 py-5">
            <div
              data-old
              className="flex items-center gap-3 rounded-sm bg-[#fdf1ee] px-3.5 py-3"
            >
              <span className="grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full bg-[#c9614a]/12 text-[#c9614a]">
                <Cross className="h-[11px] w-[11px]" />
              </span>
              <span className="relative font-mono text-[13px] text-[#a65642]">
                button “Download”
                <span
                  data-strike
                  className="absolute left-0 top-1/2 h-px w-full bg-[#a65642]"
                />
              </span>
            </div>

            <svg
              aria-hidden
              viewBox="0 0 40 60"
              className="pointer-events-none absolute right-4 top-[52px] h-[60px] w-[40px] text-moss"
            >
              <path
                data-hop
                d="M8 6 C 30 12, 30 40, 10 50"
                fill="none"
                stroke="currentColor"
                strokeOpacity="0.55"
                strokeWidth="1.6"
                strokeLinecap="round"
              />
              <path
                data-hop
                d="M10 50 L 16 44 M10 50 L 17 52"
                fill="none"
                stroke="currentColor"
                strokeOpacity="0.55"
                strokeWidth="1.6"
                strokeLinecap="round"
              />
            </svg>

            <div
              data-new
              className="mt-2.5 flex items-center gap-3 rounded-sm bg-moss/8 px-3.5 py-3"
            >
              <span className="grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full bg-moss/15 text-moss">
                <Check className="h-[11px] w-[11px]" />
              </span>
              <span className="font-mono text-[13px] text-moss">button “Get PDF”</span>
            </div>

            <p data-saved className="mt-4 px-1 text-[13.5px] text-muted">
              one step rewritten · six steps untouched
            </p>
          </div>
        </Panel>
      </ArtCard>
    </div>
  );
}
