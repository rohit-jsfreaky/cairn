"use client";

import { useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import { ArtCard } from "./ArtCard";
import { Blob } from "./Blob";
import { Check } from "./Glyphs";
import { Panel } from "./Panel";

gsap.registerPlugin(useGSAP, ScrollTrigger);

const STEPS = [
  "open the billing page",
  "sign in",
  "go to Invoices",
  "pick this month",
  "open the invoice",
  "download the PDF",
];

export function LearnArt() {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const tl = gsap.timeline({
        scrollTrigger: { trigger: root.current, start: "top 78%", once: true },
      });

      tl.from("[data-trail]", {
        scaleY: 0,
        transformOrigin: "top center",
        duration: 1.5,
        ease: "none",
      })
        .from(
          "[data-step]",
          { opacity: 0, x: -10, duration: 0.5, ease: "power2.out", stagger: 0.22 },
          0,
        )
        .from(
          "[data-tick]",
          {
            scale: 0,
            transformOrigin: "center",
            duration: 0.45,
            ease: "back.out(2.2)",
            stagger: 0.22,
          },
          0.08,
        );
    },
    { scope: root },
  );

  return (
    <div ref={root}>
      <ArtCard>
        <Blob className="-left-24 -top-20 h-[85%] w-[85%]" color="#f0cf90" />
        <Blob className="-right-16 bottom-[-10%] h-[65%] w-[70%]" color="#f7e3bc" />

        <Panel
          title="learning  billing.acme.com"
          className="absolute left-[9%] top-[13%] w-[108%]"
        >
          <ul className="relative py-3">
            <span
              aria-hidden
              data-trail
              className="absolute left-[29px] top-[30px] bottom-[30px] w-px"
              style={{
                backgroundImage:
                  "linear-gradient(to bottom, rgba(46,125,85,0.45) 0 4px, transparent 4px 11px)",
                backgroundSize: "1px 11px",
              }}
            />

            {STEPS.map((step, i) => (
              <li key={step} className="relative flex items-center gap-3.5 px-5 py-[11px]">
                <span
                  data-tick
                  className="grid h-[19px] w-[19px] shrink-0 place-items-center rounded-full bg-white text-moss ring-1 ring-moss/30"
                >
                  <Check className="h-[11px] w-[11px]" />
                </span>
                <span data-step className="flex items-baseline gap-2.5">
                  <span className="font-mono text-[11.5px] text-faint">{i + 1}</span>
                  <span className="text-[14.5px] text-ink">{step}</span>
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      </ArtCard>
    </div>
  );
}
