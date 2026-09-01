import { Container } from "./Container";
import { Eyebrow } from "./Eyebrow";
import { SplitHeading } from "./SplitHeading";
import { Reveal } from "./Reveal";

const TASKS = [
  "download the monthly invoice",
  "check the deploy dashboard",
  "pull yesterday's numbers",
  "export the payroll report",
  "file the weekly timesheet",
  "grab the bank statement",
  "renew the domain",
  "check for new tickets",
  "download the GST return",
  "update the status page",
  "reconcile the payouts",
  "collect the ad spend",
  "refill the same form",
  "check the shipment",
  "pull the error logs",
  "download the electricity bill",
  "book the same slot again",
  "copy the weekly leads",
  "chase the unpaid invoice",
  "export the support queue",
];

export function Capability() {
  return (
    <section className="hairline bg-mist py-24 sm:py-32">
      <Reveal>
        <Container className="text-center">
          <div className="flex justify-center">
            <Eyebrow>The boring work</Eyebrow>
          </div>

          <SplitHeading className="mx-auto mt-6 max-w-[900px] font-display text-[clamp(28px,3.4vw,44px)] font-medium leading-[1.1] tracking-[-0.005em] text-ink">
            Anything your AI does on a website,
            <br className="hidden sm:block" /> it only has to learn once.
          </SplitHeading>

          <div className="relative mt-16" data-reveal>
            <div className="mx-auto flex max-w-[980px] flex-wrap justify-center gap-3">
              {TASKS.map((task) => (
                <span
                  key={task}
                  className="rounded-full bg-white px-5 py-2.5 text-[15px] text-ink/75 ring-1 ring-black/5"
                >
                  {task}
                </span>
              ))}
            </div>
            <div className="pointer-events-none absolute inset-x-0 bottom-0 h-28 bg-gradient-to-b from-transparent to-mist" />
          </div>

          <p className="mx-auto mt-12 max-w-[640px] text-[18px] leading-[1.55] text-muted" data-reveal>
            None of it is clever. All of it is repeated. That is exactly the work
            worth remembering.
          </p>
        </Container>
      </Reveal>
    </section>
  );
}
