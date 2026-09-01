"use client";

import { useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import { CountUp } from "../CountUp";
import { ArtCard } from "./ArtCard";
import { Blob } from "./Blob";
import { Check } from "./Glyphs";
import { Panel } from "./Panel";

gsap.registerPlugin(useGSAP, ScrollTrigger);

const PILLS = ["1 tool call", "0 pages read", "no model used"];

export function RunArt() {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const tl = gsap.timeline({
        scrollTrigger: { trigger: root.current, start: "top 78%", once: true },
      });

      tl.from("[data-badge]", {
        scale: 0,
        opacity: 0,
        transformOrigin: "left center",
        duration: 0.5,
        ease: "back.out(2)",
        delay: 0.9,
      }).from(
        "[data-pill]",
        { y: 8, opacity: 0, duration: 0.45, ease: "power2.out", stagger: 0.08 },
        "-=0.2",
      );
    },
    { scope: root },
  );

  return (
    <div ref={root}>
      <ArtCard>
        <Blob className="-right-24 -top-16 h-[85%] w-[85%]" color="#a9d6ba" />
        <Blob className="-left-20 bottom-[-12%] h-[70%] w-[70%]" color="#d8ecdd" />

        <Panel className="absolute left-[10%] top-[16%] w-[104%]">
          <div className="px-6 pt-6 pb-7">
            <p className="font-mono text-[12.5px] text-faint">
              cairn_run · billing.acme.com
            </p>

            <div className="mt-5 flex items-end gap-3">
              <CountUp
                to={4.1}
                decimals={1}
                suffix="s"
                className="font-display text-[52px] leading-[0.9] font-medium text-ink"
              />
              <span
                data-badge
                className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-moss/12 px-2.5 py-1 text-[12.5px] font-medium text-moss"
              >
                <Check className="h-3 w-3" />
                done
              </span>
            </div>

            <p className="mt-4 text-[14.5px] text-muted">7 steps replayed from memory</p>

            <div className="mt-5 flex flex-wrap gap-2">
              {PILLS.map((pill) => (
                <span
                  key={pill}
                  data-pill
                  className="rounded-full bg-black/4 px-3 py-1.5 font-mono text-[12px] text-muted"
                >
                  {pill}
                </span>
              ))}
            </div>
          </div>
        </Panel>
      </ArtCard>
    </div>
  );
}
