import { Container } from "./Container";
import { LearnArt } from "./art/LearnArt";
import { RepairArt } from "./art/RepairArt";
import { RunArt } from "./art/RunArt";
import { Reveal } from "./Reveal";

const BEATS = [
  {
    art: <LearnArt />,
    lead: "Learns once.",
    body: "The first time, your AI walks the site through Cairn, and Cairn writes down the way.",
  },
  {
    art: <RunArt />,
    lead: "Runs in one step.",
    body: "Every time after, it follows what it wrote. No reading the page, no working it out again.",
  },
  {
    art: <RepairArt />,
    lead: "Notices when it breaks.",
    body: "A moved button stops the replay. Cairn hands your AI that one step, then saves the answer.",
  },
];

export function Beats() {
  return (
    <section className="hairline bg-white py-24 sm:py-28">
      <Reveal stagger={0.12}>
        <Container className="grid gap-6 lg:grid-cols-3">
          {BEATS.map((beat) => (
            <div key={beat.lead} data-reveal>
              {beat.art}
              <p className="mt-6 max-w-[38ch] text-[16px] leading-[1.55] text-muted">
                <span className="font-medium text-ink">{beat.lead}</span> {beat.body}
              </p>
            </div>
          ))}
        </Container>
      </Reveal>
    </section>
  );
}
