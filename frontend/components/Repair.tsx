import { Container } from "./Container";
import { Eyebrow } from "./Eyebrow";
import { Reveal } from "./Reveal";
import { SplitHeading } from "./SplitHeading";
import { TDim, TOk, TWarn, TerminalCard } from "./TerminalCard";

const POINTS = [
  {
    lead: "Every step is checked",
    body: "Cairn does not click and hope. After each step it looks at whether the page actually changed the way it should have.",
  },
  {
    lead: "Only the broken step is redone",
    body: "One button moved? Cairn hands your AI that one step to work out, writes the answer down, and the rest of the trail stays exactly as it was.",
  },
];

export function Repair() {
  return (
    <section className="hairline bg-white py-24 sm:py-32">
      <Reveal>
        <Container className="grid items-center gap-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-16">
          <div>
            <Eyebrow>Sites change</Eyebrow>

            <SplitHeading className="mt-6 max-w-[15ch] font-display text-[clamp(28px,3.2vw,42px)] font-medium leading-[1.1] text-ink">
              When the site changes, it does not start over.
            </SplitHeading>

            <p className="mt-6 max-w-[46ch] text-[18px] leading-[1.55] text-muted" data-reveal>
              A saved playbook usually snaps the first time a button moves. Cairn checks
              every step, so it notices — then only the step that moved goes back to
              your AI, and the answer is saved for next time.
            </p>

            <div className="mt-12 space-y-8">
              {POINTS.map((point) => (
                <div key={point.lead} data-reveal>
                  <p className="text-[16px] font-medium text-ink">{point.lead}</p>
                  <p className="mt-2.5 max-w-[46ch] text-[15px] leading-[1.55] text-muted">
                    {point.body}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div data-reveal>
            <TerminalCard title="the day the billing portal was redesigned">
              <TOk>steps 1–4 replayed from memory</TOk>
              <TWarn>step 5 did not land — the page did not change</TWarn>
              <div className="h-4" />
              <TDim>cairn handed me step 5, and nothing else</TDim>
              <TOk>“Download” is now “Get PDF”</TOk>
              <TOk>cairn saved the fix to the trail</TOk>
              <div className="h-4" />
              <TOk>steps 6–7 replayed from memory</TOk>
              <p className="mt-4 text-faint">
                next run: 7 of 7 from memory, nothing to work out
              </p>
            </TerminalCard>
          </div>
        </Container>
      </Reveal>
    </section>
  );
}
