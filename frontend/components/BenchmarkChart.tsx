"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/**
 * The GitHub task as a RUNNING TOTAL, which is the only shape that shows a gap growing.
 *
 * Bars per run were the first attempt and they showed the wrong thing — a flat line beside
 * a bumpy one. The claim is not "our runs are steady", it is "the difference keeps getting
 * bigger", and that is a cumulative curve or it is nothing.
 *
 * All three tools are drawn, including the one that runs Cairn close here. Chrome DevTools
 * MCP is genuinely efficient on GitHub — three calls a run — and dropping that line to
 * flatter the picture would make the whole chart worthless. The crossing point, where
 * Cairn's learning run stops costing more than their tenth, is the honest story.
 */
const CUMULATIVE = [
  { run: 1, cairn: 10, playwright: 8, devtools: 3 },
  { run: 2, cairn: 12, playwright: 16, devtools: 6 },
  { run: 3, cairn: 14, playwright: 34, devtools: 9 },
  { run: 4, cairn: 16, playwright: 41, devtools: 12 },
  { run: 5, cairn: 18, playwright: 50, devtools: 18 },
  { run: 6, cairn: 20, playwright: 59, devtools: 21 },
  { run: 7, cairn: 22, playwright: 66, devtools: 24 },
  { run: 8, cairn: 24, playwright: 72, devtools: 27 },
  { run: 9, cairn: 26, playwright: 77, devtools: 30 },
  { run: 10, cairn: 28, playwright: 83, devtools: 33 },
];

const MOSS = "#2e7d55";
const GREY = "#9a9a9a";
const FAINT = "#c4c4c4";

const NAMES: Record<string, string> = {
  cairn: "Cairn",
  playwright: "Playwright MCP",
  devtools: "Chrome DevTools MCP",
};

type Point = { name?: string; dataKey?: string | number; value?: number | string };

function Card({ active, payload, label }: { active?: boolean; payload?: Point[]; label?: number }) {
  if (!active || !payload?.length) return null;
  const rows = [...payload].sort((a, b) => Number(a.value ?? 0) - Number(b.value ?? 0));
  return (
    <div className="surface rounded-sm bg-white px-4 py-3 text-[13px] shadow-[0_8px_28px_rgba(0,0,0,0.10)]">
      <p className="mb-2 text-[12px] uppercase tracking-[0.08em] text-faint">
        after run {label}
      </p>
      {rows.map((row) => {
        const key = String(row.dataKey);
        return (
          <p key={key} className="flex items-baseline justify-between gap-6 py-0.5">
            <span className={key === "cairn" ? "font-medium text-moss" : "text-muted"}>
              {NAMES[key]}
            </span>
            <span
              className={`font-mono ${key === "cairn" ? "text-moss" : "text-ink/70"}`}
            >
              {row.value} calls
            </span>
          </p>
        );
      })}
    </div>
  );
}

export function BenchmarkChart() {
  return (
    <div className="h-[330px] w-full sm:h-[380px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={CUMULATIVE} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid stroke="#0a0b0c" strokeOpacity={0.06} vertical={false} />
          <XAxis
            dataKey="run"
            tickFormatter={(run) => `run ${run}`}
            tick={{ fill: "#a1a1a1", fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: "#0a0b0c", strokeOpacity: 0.14 }}
            dy={8}
          />
          <YAxis
            tick={{ fill: "#a1a1a1", fontSize: 12, fontFamily: "ui-monospace, monospace" }}
            tickLine={false}
            axisLine={false}
            width={42}
            domain={[0, 90]}
            ticks={[0, 30, 60, 90]}
            label={{
              value: "tool calls, running total",
              angle: -90,
              position: "insideLeft",
              style: { fill: "#c4c4c4", fontSize: 11, textAnchor: "middle" },
            }}
          />
          <Tooltip
            content={<Card />}
            cursor={{ stroke: "#0a0b0c", strokeOpacity: 0.18, strokeDasharray: "4 4" }}
          />
          <Legend
            verticalAlign="top"
            align="left"
            height={40}
            iconType="plainline"
            formatter={(value: string) => (
              <span
                className={
                  value === "Cairn"
                    ? "text-[14px] font-medium text-moss"
                    : "text-[14px] text-muted"
                }
              >
                {value}
              </span>
            )}
          />
          <Line
            name="Playwright MCP"
            type="monotone"
            dataKey="playwright"
            stroke={GREY}
            strokeWidth={1.75}
            dot={false}
            activeDot={{ r: 4, fill: GREY, stroke: "#fff", strokeWidth: 2 }}
          />
          <Line
            name="Chrome DevTools MCP"
            type="monotone"
            dataKey="devtools"
            stroke={FAINT}
            strokeWidth={1.75}
            strokeDasharray="5 4"
            dot={false}
            activeDot={{ r: 4, fill: FAINT, stroke: "#fff", strokeWidth: 2 }}
          />
          <Line
            name="Cairn"
            type="monotone"
            dataKey="cairn"
            stroke={MOSS}
            strokeWidth={2.75}
            dot={false}
            activeDot={{ r: 5, fill: MOSS, stroke: "#fff", strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
