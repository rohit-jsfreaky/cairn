"use client";

import { useState } from "react";

/**
 * The head to head, one task at a time.
 *
 * Shape borrowed from the way tools that live on benchmarks present them (bun.sh, checked
 * 2026-09-05): tabs so only ONE comparison is on screen, the tool name in a column to the
 * LEFT of the plot rather than inside it, the number at the end of its own bar, a scale
 * along the bottom, and the exact conditions written underneath.
 *
 * Three earlier attempts failed for the same reason: everything was inside the chart. A
 * table made the reader do the arithmetic, stacked bar groups put four comparisons on
 * screen at once, and a charting library drew the tool names over the bars. Labels belong
 * outside the plot, and only one question belongs on screen at a time.
 */
type Bar = { tool: string; calls: number; tokens: string; ours?: boolean };

type Task = {
  id: string;
  tab: string;
  heading: string;
  site: string;
  ceiling: number;
  step: number;
  bars: Bar[];
};

const TASKS: Task[] = [
  {
    id: "github",
    tab: "GitHub issues",
    heading: "Open a repo, go to Issues, count them",
    site: "github.com/microsoft/playwright",
    ceiling: 100,
    step: 25,
    bars: [
      { tool: "Cairn", calls: 28, tokens: "1.4M", ours: true },
      { tool: "Chrome DevTools MCP", calls: 33, tokens: "1.7M" },
      { tool: "Playwright MCP", calls: 83, tokens: "3.4M" },
    ],
  },
  {
    id: "quotes",
    tab: "Author's birth date",
    heading: "Open an author's page, read their birth date",
    site: "quotes.toscrape.com",
    ceiling: 80,
    step: 20,
    bars: [
      { tool: "Cairn", calls: 27, tokens: "1.3M", ours: true },
      { tool: "Chrome DevTools MCP", calls: 60, tokens: "2.6M" },
      { tool: "Playwright MCP", calls: 60, tokens: "2.6M" },
    ],
  },
  {
    id: "books",
    tab: "Book price",
    heading: "Open a category, open a book, read its price",
    site: "books.toscrape.com",
    ceiling: 80,
    step: 20,
    bars: [
      { tool: "Cairn", calls: 41, tokens: "1.9M", ours: true },
      { tool: "Chrome DevTools MCP", calls: 56, tokens: "2.8M" },
      { tool: "Playwright MCP", calls: 56, tokens: "2.8M" },
    ],
  },
  {
    id: "all",
    tab: "All three",
    heading: "Every task above, added up",
    site: "90 fresh Claude sessions",
    ceiling: 200,
    step: 50,
    bars: [
      { tool: "Cairn", calls: 96, tokens: "4.6M", ours: true },
      { tool: "Chrome DevTools MCP", calls: 149, tokens: "7.1M" },
      { tool: "Playwright MCP", calls: 199, tokens: "8.7M" },
    ],
  },
];

export function TaskChart() {
  const [open, setOpen] = useState(TASKS[0].id);
  const task = TASKS.find((one) => one.id === open) ?? TASKS[0];
  const ticks = Array.from(
    { length: Math.floor(task.ceiling / task.step) + 1 },
    (_, at) => at * task.step,
  );

  return (
    <div className="border rounded-2xl border-ink/10 rounded-lg bg-white p-6 sm:p-9">
      {/* ------------------------------------------------------------------- tabs */}
      <div className="well inline-flex flex-wrap gap-1 rounded-full bg-mist p-1">
        {TASKS.map((one) => (
          <button
            key={one.id}
            type="button"
            onClick={() => setOpen(one.id)}
            aria-pressed={one.id === open}
            className={`rounded-full px-4 py-2 text-[14px] font-medium transition-colors sm:px-5 ${
              one.id === open
                ? "surface bg-white text-ink"
                : "text-muted hover:text-ink"
            }`}
          >
            {one.tab}
          </button>
        ))}
      </div>

      {/* ---------------------------------------------------------------- heading */}
      <div className="mt-8 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h4 className="text-[19px] font-medium leading-[1.3] text-ink">{task.heading}</h4>
        <p className="font-mono text-[13px] text-faint">{task.site}</p>
      </div>
      <p className="mt-1.5 text-[14px] text-muted">
        10 runs · tool calls · lower is better
      </p>

      {/* ------------------------------------------------------------------- bars */}
      <div className="mt-8 space-y-3">
        {task.bars.map((bar) => (
          <div key={bar.tool} className="group flex items-center gap-4">
            <span
              className={`w-[112px] shrink-0 text-right text-[14px] leading-[1.25] sm:w-[176px] ${
                bar.ours ? "font-medium text-moss" : "text-muted"
              }`}
            >
              {bar.tool}
            </span>

            <span className="relative min-w-0 flex-1">
              <span
                className={`block h-[30px] rounded-xs transition-[width] duration-500 ease-out ${
                  bar.ours ? "bg-moss" : "bg-black/10"
                }`}
                style={{ width: `${(bar.calls / task.ceiling) * 100}%` }}
              />
              <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center opacity-0 transition-opacity group-hover:opacity-100">
                <span
                  className="ml-3 font-mono text-[12.5px]"
                  style={{ color: bar.ours ? "#ffffff" : "#737373" }}
                >
                  {bar.tokens} tokens
                </span>
              </span>
            </span>

            <span className="flex w-[74px] shrink-0 items-baseline justify-end gap-1.5">
              <span
                className={`font-mono text-[17px] ${
                  bar.ours ? "font-semibold text-moss" : "text-ink/70"
                }`}
              >
                {bar.calls}
              </span>
              <span className="text-[12px] text-faint">calls</span>
            </span>
          </div>
        ))}
      </div>

      {/* ------------------------------------------------------------------ scale */}
      <div className="mt-3 flex items-center gap-4" aria-hidden>
        <span className="w-[112px] shrink-0 sm:w-[176px]" />
        <span className="relative min-w-0 flex-1 border-t border-black/10 pt-2">
          <span className="flex justify-between font-mono text-[11.5px] text-faint">
            {ticks.map((tick) => (
              <span key={tick}>{tick}</span>
            ))}
          </span>
        </span>
        <span className="w-[74px] shrink-0" />
      </div>

      {/* ---------------------------------------------------------------- caption */}
      <p className="mt-8 border-t border-black/6 pt-6 text-[13.5px] leading-[1.6] text-faint">
        Each run is a brand-new Claude session (Sonnet 5, medium) with nothing carried over
        but Cairn&apos;s memory · Playwright MCP 0.0.80 and Chrome DevTools MCP 1.8.0, both
        pinned · every tool answered correctly 30 times out of 30 · hover a bar for its
        token count
      </p>
    </div>
  );
}
