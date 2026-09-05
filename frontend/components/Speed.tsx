"use client";

import { useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import { Container } from "./Container";
import { SplitHeading } from "./SplitHeading";

gsap.registerPlugin(useGSAP, ScrollTrigger);

/**
 * The same task on a REAL site, ten times, each time in a brand-new Claude session.
 *
 * This used to be five mornings on the demo site in this repo, which was the weakest
 * evidence on the page: our own toy site, driven by a script, with no model in it. Every
 * number here comes from `package/benchmark_agents.py --journeys --runs 10` instead —
 * github.com/microsoft/playwright, open the Issues tab, report the open count. A real
 * multi-step task, a real Claude session per run (Sonnet 5, medium), nothing carried over
 * between runs but Cairn's memory.
 *
 * Drawn as ten COLUMNS rather than ten rows. Ten stacked horizontal bars was a tall,
 * repetitive list, and it copied the shape of the head-to-head section above it. What is
 * worth seeing here is not each run — it is the cliff between the first one and all the
 * rest, and a cliff is a silhouette that wants to be read left to right.
 *
 * `model calls` is deliberately not one of the metrics. Cairn's replay makes none — it is
 * plain Python — but the host session still thinks about what to call and how to answer,
 * so a figure of zero here would be true of the engine and false of the screen.
 */
type Metric = {
  id: string;
  label: string;
  values: number[];
  display: (value: number) => string;
  cold: string;
  warm: string;
};

const METRICS: Metric[] = [
  {
    id: "calls",
    label: "Tool calls",
    values: [10, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    display: (value) => String(value),
    cold: "10 calls",
    warm: "2 calls",
  },
  {
    id: "tokens",
    label: "Tokens",
    values: [
      421407, 103799, 103823, 103773, 103834, 104024, 106438, 103817, 103977, 103968,
    ],
    display: (value) => Math.round(value / 1000) + "k",
    cold: "421k tokens",
    warm: "104k tokens",
  },
  {
    id: "time",
    label: "Time to finish",
    values: [44.5, 12.5, 13.5, 15.7, 14.6, 14.8, 14.3, 15.3, 14.1, 18.7],
    display: (value) => value.toFixed(1) + "s",
    cold: "44.5 seconds",
    warm: "12.5 seconds",
  },
];

const TALLEST = 180;

export function Speed() {
  const [open, setOpen] = useState(METRICS[0].id);
  const metric = METRICS.find((one) => one.id === open) ?? METRICS[0];
  const ceiling = Math.max(...metric.values);
  const root = useRef<HTMLDivElement>(null);
  const first = useRef(true);

  useGSAP(
    () => {
      const columns = gsap.utils.toArray<HTMLElement>("[data-column]");
      if (!columns.length) return;

      const from = { scaleY: 0, transformOrigin: "bottom center" };
      const to = {
        scaleY: 1,
        transformOrigin: "bottom center",
        duration: 0.75,
        ease: "power3.out",
        stagger: 0.045,
      };

      if (first.current) {
        first.current = false;
        gsap.from(columns, {
          ...from,
          ...to,
          scrollTrigger: { trigger: root.current, start: "top 82%", once: true },
        });
        return;
      }
      gsap.fromTo(columns, from, to);
    },
    { scope: root, dependencies: [open] },
  );

  return (
    <section id="speed" className="hairline scroll-mt-16 bg-white py-24 sm:py-32">
      <Container>
        <div className="mx-auto max-w-[1000px]">
          <SplitHeading className="max-w-[18ch] font-display text-[clamp(28px,3.4vw,44px)] font-medium leading-[1.1] text-ink">
            The second run is where you get your time back.
          </SplitHeading>

          <p className="mt-6 max-w-[64ch] text-[19px] leading-[1.5] text-muted">
            One real task on a real site — open a GitHub repo, go to Issues, report the open
            count — run ten times, each time in a brand-new Claude session with nothing
            carried over but Cairn&apos;s memory. Run one walks the site and writes down the
            way. Every run after it follows the way instead.
          </p>

          <div className=" mt-14 roun-lg bg-white p-6 sm:p-ded9 border rounded-2xl border-ink/10">
            {/* --------------------------------------------------- the claim, in words */}
            <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-5">
              <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <span className="font-mono text-[15px] text-muted">{metric.cold}</span>
                <span aria-hidden className="text-faint">
                  →
                </span>
                <span className="font-mono text-[22px] font-semibold text-moss">
                  {metric.warm}
                </span>
                <span className="text-[14px] text-faint">every run after</span>
              </p>

              <div className="well inline-flex rounded-full bg-mist p-1">
                {METRICS.map((one) => (
                  <button
                    key={one.id}
                    type="button"
                    onClick={() => setOpen(one.id)}
                    aria-pressed={one.id === open}
                    className={`rounded-full px-4 py-2 text-[13.5px] font-medium transition-colors ${
                      one.id === open
                        ? "surface bg-white text-ink"
                        : "text-muted hover:text-ink"
                    }`}
                  >
                    {one.label}
                  </button>
                ))}
              </div>
            </div>

            {/* ------------------------------------------------------------ the cliff */}
            {/*
              The columns sit INSIDE a recessed plot area rather than on a drawn axis line.
              A 1px rule at the site's own 6% hairline weight vanished at Windows display
              scaling, and thickening it would have made the one heavy line on the page.
              The well gives the bars a floor you cannot miss, in the language the rest of
              the site already speaks.
            */}
            <div ref={root} className=" mt-10 rounded-md px-4 pt-6 pb-4 sm:px-6">
              <div className="flex items-end gap-2 sm:gap-3" style={{ height: TALLEST + 42 }}>
                {metric.values.map((value, at) => (
                  <div key={at} className="flex h-full flex-1 flex-col justify-end">
                    {(at === 0 || at === 1) && (
                      <span
                        className={`mb-1 whitespace-nowrap text-center text-[11.5px] ${
                          at === 0 ? "text-faint" : "text-moss/75"
                        }`}
                      >
                        {at === 0 ? "learning" : "remembered"}
                      </span>
                    )}
                    <span
                      className={`mb-2 text-center font-mono text-[12px] ${
                        at === 0 ? "text-muted" : "text-moss"
                      }`}
                    >
                      {metric.display(value)}
                    </span>
                    <span
                      data-column
                      className={`w-full rounded-t-xs ${
                        at === 0 ? "bg-ink/15" : "bg-moss"
                      }`}
                      style={{ height: (value / ceiling) * TALLEST }}
                    />
                  </div>
                ))}
              </div>

              <div className="mt-3 flex gap-2 border-t border-black/10 pt-3 sm:gap-3">
                {metric.values.map((_, at) => (
                  <span
                    key={at}
                    className={`flex-1 text-center text-[12px] ${
                      at === 0 ? "text-muted" : "text-faint"
                    }`}
                  >
                    {at + 1}
                  </span>
                ))}
              </div>
              <p className="mt-2 text-center text-[12px] text-faint">
                run number — each one a brand-new session
              </p>
            </div>

            <p className="mt-8 border-t border-black/6 pt-6 text-[13.5px] leading-[1.6] text-faint">
              The first column is the run that learned the site: Cairn does the job and
              writes down the way at the same time. Nine runs later it is still two calls,
              because nothing has to be worked out twice.
            </p>
          </div>
        </div>
      </Container>
    </section>
  );
}
