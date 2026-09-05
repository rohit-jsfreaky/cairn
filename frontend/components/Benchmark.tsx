import { BenchmarkChart } from "./BenchmarkChart";
import { Container } from "./Container";
import { Eyebrow } from "./Eyebrow";
import { Reveal } from "./Reveal";
import { SplitHeading } from "./SplitHeading";
import { TaskChart } from "./TaskChart";

/**
 * The head to head, and every number in it is measured.
 *
 * Three multi-step tasks on public sites, each done ten times, every run a FRESH Claude
 * session with nothing carried over but Cairn's memory. Sonnet 5 at medium effort, against
 * `@playwright/mcp@0.0.80` and `chrome-devtools-mcp@1.8.0`, both pinned so a rerun measures
 * the same thing. 90 sessions in total.
 *
 * The tasks are multi-step ON PURPOSE, and the honest reason is in the README: measured on
 * one-page lookups the same comparison is nearly a tie, because opening one page and
 * reading one line costs everybody two or three calls and leaves memory nothing to save.
 * Real work has steps, and a step is what a browser tool charges for.
 */
export function Benchmark() {
  return (
    <section id="numbers" className="hairline scroll-mt-16 bg-white py-24 sm:py-32">
      <Reveal>
        <Container>
          <div className="mx-auto max-w-[1080px]">
            <Eyebrow>Measured, not claimed</Eyebrow>

            <SplitHeading className="mt-6 max-w-[20ch] font-display text-[clamp(28px,3.4vw,44px)] font-medium leading-[1.1] text-ink">
              Half the tool calls of a browser that forgets.
            </SplitHeading>

            <p className="mt-6 max-w-[64ch] text-[19px] leading-[1.5] text-muted" data-reveal>
              The same job, done ten times, each time in a brand-new chat. Three real
              multi-step tasks, three browser tools, 90 fresh Claude sessions. Every tool
              answered correctly 30 times out of 30.
            </p>

            {/* ------------------------------------------------------------- the rows */}
            <div className="mt-14" data-reveal>
              <TaskChart />
            </div>

            {/* -------------------------------------------------------- the headline */}
            <div
              className="mt-12 grid gap-px overflow-hidden rounded-lg bg-black/8 sm:grid-cols-2"
              data-reveal
            >
              <Claim
                number="52%"
                what="fewer tool calls than Playwright MCP"
                sub="47% fewer tokens"
              />
              <Claim
                number="36%"
                what="fewer tool calls than Chrome DevTools MCP"
                sub="35% fewer tokens"
              />
            </div>

            {/* ------------------------------------------------------------ the shape */}
            <div className="mt-20" data-reveal>
              <h3 className="font-display text-[clamp(22px,2.4vw,30px)] font-medium leading-[1.15] text-ink">
                And the gap grows every time you run it.
              </h3>
              <p className="mt-4 max-w-[62ch] text-[17px] leading-[1.55] text-muted">
                The GitHub task, as a running total. Cairn pays once to learn the route,
                then costs two calls — however many steps that route has. The others start
                from nothing every single time, because they are not trying to remember.
                Hover any point to read all three.
              </p>

              <div className="mt-8">
                <BenchmarkChart />
              </div>

              <p className="mt-4 text-[14px] text-faint">
                Cairn is the most expensive tool for the first three runs — it does the job
                and learns the route at the same time — and the cheapest from then on.
              </p>
            </div>

            {/* ------------------------------------------------------- one honest line */}
            <p
              className="mt-16 max-w-[76ch] text-[15px] leading-[1.6] text-faint"
              data-reveal
            >
              Measured over 90 fresh Claude sessions, against pinned versions of both tools.
              Cairn is the expensive one on the first run — it does the job and learns the
              route at the same time — and on a single page with a one-line answer it is not
              cheaper at all, because there is nothing for memory to save.
            </p>

          </div>
        </Container>
      </Reveal>
    </section>
  );
}

function Claim({ number, what, sub }: { number: string; what: string; sub: string }) {
  return (
    <div className="bg-white px-8 py-10">
      <p className="font-display text-[clamp(40px,6vw,64px)] font-medium leading-none text-moss">
        {number}
      </p>
      <p className="mt-4 max-w-[26ch] text-[18px] leading-[1.4] text-ink">{what}</p>
      <p className="mt-1 text-[15px] text-faint">{sub}</p>
    </div>
  );
}
