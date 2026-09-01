import { Container } from "./Container";
import { Eyebrow } from "./Eyebrow";
import { SplitHeading } from "./SplitHeading";
import { MemoryArt } from "./art/MemoryArt";
import { Reveal } from "./Reveal";

const POINTS = [
  {
    lead: "It is a file, not a chat",
    body: "What Cairn learns is written to your disk, not held inside a conversation.",
  },
  {
    lead: "Quit anything you like",
    body: "Close the terminal, restart the machine, come back next week.",
  },
  {
    lead: "Ask again, it just goes",
    body: "No warm-up, no re-explaining, no pasting yesterday's notes back in.",
  },
];

export function FreshSession() {
  return (
    <section className="hairline overflow-hidden bg-mist pt-24 sm:pt-32">
      <Reveal>
        <Container className="text-center">
          <div className="flex justify-center">
            <Eyebrow>Memory that lasts</Eyebrow>
          </div>

          <SplitHeading className="mx-auto mt-6 max-w-[760px] font-display text-[clamp(28px,3.4vw,44px)] font-medium leading-[1.1] text-ink">
            Close your editor. It still remembers.
          </SplitHeading>
          <p className="mx-auto mt-6 max-w-[640px] text-[18px] leading-[1.55] text-muted" data-reveal>
            Most AI memory disappears the moment the session ends. Cairn keeps the
            trail on your own machine, so tomorrow starts where today stopped.
          </p>

          <div
            className="mx-auto mt-14 grid max-w-[1000px] gap-10 text-left sm:grid-cols-3"
            data-reveal
          >
            {POINTS.map((point) => (
              <div key={point.lead}>
                <p className="text-[16px] font-medium text-ink">{point.lead}</p>
                <p className="mt-2.5 text-[15px] leading-[1.55] text-muted">{point.body}</p>
              </div>
            ))}
          </div>

          <div className="mx-auto mt-16 mb-[-72px] max-w-[1000px] text-left">
            <MemoryArt />
          </div>
        </Container>
      </Reveal>
    </section>
  );
}
