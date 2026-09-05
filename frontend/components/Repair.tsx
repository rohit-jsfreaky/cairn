import { Container } from "./Container";
import { Eyebrow } from "./Eyebrow";
import { Reveal } from "./Reveal";
import { SplitHeading } from "./SplitHeading";

/**
 * Repair, shown as the artefact rather than described in prose.
 *
 * Two earlier versions of this section were a text column beside a card with a bulleted
 * list under it — the layout this page already used twice, and the one every product page
 * uses. Redesigned 2026-09-05 after looking at how sites that do this well actually do it
 * (linear.app, graphite.com): an asymmetric pair of cards rather than a symmetric split,
 * and the real thing inside the big one rather than a drawing of it.
 *
 * The real thing here is the trail — seven stored steps — and a repair is one line of it
 * changing. So it is drawn the way a developer already reads a change: a diff. The old
 * locator struck through, the new one added, and every other step visibly untouched. No
 * warning colour is needed and none exists in this palette; a struck line and a moss line
 * carry it.
 */
type Step = {
  n: number;
  action: string;
  target: string;
  state: "memory" | "gone" | "fixed";
};

const TRAIL: Step[] = [
  { n: 1, action: "open", target: "the invoices page", state: "memory" },
  { n: 2, action: "click", target: '"August 2026"', state: "memory" },
  { n: 3, action: "click", target: '"Billing"', state: "memory" },
  { n: 4, action: "wait", target: "for the table to settle", state: "memory" },
  { n: 5, action: "click", target: '"Download"', state: "gone" },
  { n: 5, action: "click", target: '"Get PDF"', state: "fixed" },
  { n: 6, action: "read", target: "the invoice total", state: "memory" },
  { n: 7, action: "check", target: "the file is on disk", state: "memory" },
];

export function Repair() {
  return (
    <section className="hairline bg-white py-24 sm:py-32">
      <Reveal>
        <Container>
          <div className="mx-auto max-w-[1100px]">
            <Eyebrow>Sites change</Eyebrow>

            <SplitHeading className="mt-6 max-w-[22ch] font-display text-[clamp(28px,3.4vw,44px)] font-medium leading-[1.1] text-ink">
              One line of the trail changes. Not the trail.
            </SplitHeading>

            <p className="mt-6 max-w-[62ch] text-[19px] leading-[1.5] text-muted" data-reveal>
              Cairn checks that every step actually landed, so it notices the moment one
              stops working — and only that step goes back to your AI. Here is what a
              redesign did to a seven-step trail.
            </p>

            <div className="mt-14 grid gap-5 lg:grid-cols-3">
              {/* ------------------------------------------------- the artefact itself */}
              <div className="surface overflow-hidden rounded-lg bg-white lg:col-span-2">
                <div className="flex items-center justify-between gap-4 border-b border-black/6 bg-soft px-5 py-3.5 sm:px-7">
                  <p className="font-mono text-[13px] text-muted">
                    billing.acme.com{" "}
                    <span className="text-faint">· download this month&apos;s invoice</span>
                  </p>
                  <p className="shrink-0 font-mono text-[12px] text-faint">7 steps</p>
                </div>

                <div className="px-5 py-4 sm:px-7 sm:py-5">
                  {TRAIL.map((step, at) => (
                    <Line key={at} step={step} />
                  ))}
                </div>

                <p className="border-t border-black/6 px-5 py-4 text-[13.5px] text-faint sm:px-7">
                  Six steps were never touched. The seventh was rewritten once and is part
                  of the trail from now on.
                </p>
              </div>

              {/* -------------------------------------------------------- what it cost */}
              <div className="flex flex-col gap-5">
                <div className="surface flex-1 rounded-lg bg-white p-7">
                  <p className="font-display text-[56px] font-medium leading-none text-moss">
                    3
                  </p>
                  <p className="mt-3 text-[17px] leading-[1.35] text-ink">
                    calls to repair the step that moved
                  </p>
                  <p className="mt-2 text-[15px] leading-[1.5] text-muted">
                    Learning that trail from scratch costs 9. The next run is back to 1.
                  </p>
                </div>

                <div className="well rounded-lg bg-mist p-7">
                  <p className="text-[15px] font-medium text-ink">
                    Nothing is guessed at
                  </p>
                  <p className="mt-2 text-[15px] leading-[1.55] text-muted">
                    Cairn will not bind a step to a control it is not sure about. If several
                    things could be the button, it stops and asks rather than clicking the
                    wrong one for the next year.
                  </p>
                </div>
              </div>
            </div>

            <p
              className="mt-10 text-[14px] leading-[1.6] text-faint"
              data-reveal
            >
              Measured on a site we can change on purpose — a real one cannot be asked to
              redesign itself on cue.
            </p>
          </div>
        </Container>
      </Reveal>
    </section>
  );
}

/** One stored step. The two that changed are drawn the way a diff is read. */
function Line({ step }: { step: Step }) {
  const gone = step.state === "gone";
  const fixed = step.state === "fixed";

  return (
    <div
      className={`-mx-3 flex items-baseline gap-3 rounded-xs px-3 py-[7px] font-mono text-[13.5px] sm:gap-4 ${
        gone ? "bg-black/[0.035]" : fixed ? "bg-moss/8" : ""
      }`}
    >
      <span
        aria-hidden
        className={`w-[10px] shrink-0 ${
          gone ? "text-faint" : fixed ? "text-moss" : "text-transparent"
        }`}
      >
        {gone ? "−" : fixed ? "+" : "·"}
      </span>

      <span className={`w-[14px] shrink-0 ${fixed ? "text-moss" : "text-faint"}`}>
        {step.n}
      </span>

      <span
        className={`shrink-0 ${
          gone ? "text-faint line-through" : fixed ? "text-moss" : "text-muted"
        }`}
      >
        {step.action}
      </span>

      <span
        className={`min-w-0 flex-1 truncate ${
          gone ? "text-faint line-through" : fixed ? "text-moss" : "text-ink"
        }`}
      >
        {step.target}
      </span>

      <span
        className={`shrink-0 text-[12px] ${
          gone ? "text-faint" : fixed ? "text-moss" : "text-faint"
        }`}
      >
        {gone ? "no longer on the page" : fixed ? "your AI, once" : "from memory"}
      </span>
    </div>
  );
}
