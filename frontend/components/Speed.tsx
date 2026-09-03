"use client";

import { useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import { CairnMark } from "./CairnMark";
import { Container } from "./Container";
import { SplitHeading } from "./SplitHeading";

gsap.registerPlugin(useGSAP, ScrollTrigger);

type Run = {
  label: string;
  note?: string;
  learning?: boolean;
  values: Record<string, { display: string; fill: number }>;
};

/**
 * The same task, on the same site, five mornings running.
 *
 * Measured, not illustrative. Every number below is printed by `package/benchmark.py`,
 * which runs a real browser against the demo site in this repo — including Thursday, where
 * `?variant=b` renames and moves the controls on purpose. Run it yourself:
 *
 *     .venv/Scripts/python package/benchmark.py
 */
const RUNS: Run[] = [
  {
    label: "Monday",
    note: "learning the site",
    learning: true,
    values: {
      calls: { display: "9", fill: 100 },
      reads: { display: "3", fill: 100 },
      time: { display: "0.8s", fill: 100 },
    },
  },
  {
    label: "Tuesday",
    note: "from memory",
    values: {
      calls: { display: "1", fill: 11.1 },
      reads: { display: "0", fill: 0 },
      time: { display: "0.4s", fill: 50 },
    },
  },
  {
    label: "Wednesday",
    note: "from memory",
    values: {
      calls: { display: "1", fill: 11.1 },
      reads: { display: "0", fill: 0 },
      time: { display: "0.4s", fill: 50 },
    },
  },
  {
    label: "Thursday",
    note: "the site changed, one step repaired",
    values: {
      calls: { display: "3", fill: 33.3 },
      reads: { display: "0", fill: 0 },
      time: { display: "6.4s", fill: 100 },
    },
  },
  {
    label: "Friday",
    note: "from memory",
    values: {
      calls: { display: "1", fill: 11.1 },
      reads: { display: "0", fill: 0 },
      time: { display: "0.5s", fill: 62.5 },
    },
  },
];

/**
 * Calls first, on purpose. The clock is the least honest column here: this benchmark has
 * no model thinking in it, and thinking is the cost memory actually removes.
 */
const METRICS = [
  { id: "calls", label: "Tool calls" },
  { id: "reads", label: "Pages read" },
  { id: "time", label: "Time to finish" },
];

export function Speed() {
  const [metric, setMetric] = useState(METRICS[0].id);
  const root = useRef<HTMLDivElement>(null);
  const first = useRef(true);

  useGSAP(
    () => {
      const bars = gsap.utils.toArray<HTMLElement>("[data-bar]");
      if (!bars.length) return;

      if (first.current) {
        first.current = false;
        gsap.from(bars, {
          scaleX: 0,
          transformOrigin: "left center",
          duration: 1.1,
          ease: "power3.out",
          stagger: 0.09,
          scrollTrigger: { trigger: root.current, start: "top 80%", once: true },
        });
        return;
      }

      gsap.fromTo(
        bars,
        { scaleX: 0 },
        {
          scaleX: 1,
          transformOrigin: "left center",
          duration: 0.8,
          ease: "power3.out",
          stagger: 0.06,
        },
      );
    },
    { scope: root, dependencies: [metric] },
  );

  return (
    <section id="speed" className="hairline scroll-mt-16 bg-white py-24 sm:py-32">
      <Container>
        <div className="mx-auto max-w-[1000px]">
          <SplitHeading className="max-w-[18ch] font-display text-[clamp(28px,3.4vw,44px)] font-medium leading-[1.1] text-ink">
            The second run is where you get your time back.
          </SplitHeading>

          <p className="mt-6 max-w-[62ch] text-[19px] leading-[1.5] text-muted">
            The same task, on the same site, five mornings in a row. Cairn walks it
            once on Monday and writes down the way. On Thursday the portal was
            redesigned and it repaired the one step that moved. These are measured
            numbers — <code className="font-mono text-[15px]">package/benchmark.py</code>{" "}
            prints them, and you can run it.{" "}
            <a
              href="#what"
              className="text-moss underline decoration-moss/30 underline-offset-4 transition-colors hover:decoration-moss"
            >
              See how it works
            </a>
          </p>

          <div ref={root} className="mt-16">
            {RUNS.map((run) => {
              const value = run.values[metric];
              return (
                <div
                  key={run.label}
                  className="flex items-center gap-6 border-b border-black/6 py-4"
                >
                  <span className="flex w-[190px] shrink-0 items-center gap-3 sm:w-[250px]">
                    <span
                      className={`grid h-[26px] w-[26px] shrink-0 place-items-center rounded-full ${
                        run.learning
                          ? "bg-black/5 text-faint"
                          : "bg-moss/12 text-moss"
                      }`}
                    >
                      <CairnMark className="h-[13px] w-[13px]" />
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate text-[15px] text-ink">
                        {run.label}
                      </span>
                      <span className="block truncate text-[12.5px] text-faint">
                        {run.note}
                      </span>
                    </span>
                  </span>

                  <span className="min-w-0 flex-1">
                    <span
                      data-bar
                      className={`block h-[26px] rounded-xs ${
                        run.learning ? "bg-black/8" : "bg-moss"
                      }`}
                      style={{ width: `${Math.max(value.fill, 1.4)}%` }}
                    />
                  </span>

                  <span
                    className={`w-[88px] shrink-0 text-right font-mono text-[16px] ${
                      run.learning ? "text-muted" : "text-ink"
                    }`}
                  >
                    {value.display}
                  </span>
                </div>
              );
            })}
          </div>

          <div className="mt-10 flex justify-center">
            <div className="well inline-flex rounded-full bg-mist p-1">
              {METRICS.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setMetric(m.id)}
                  className={`rounded-full px-5 py-2.5 text-[14px] font-medium transition-colors ${
                    m.id === metric
                      ? "surface bg-white text-ink"
                      : "text-muted hover:text-ink"
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Container>
    </section>
  );
}
