import { Container } from "./Container";
import { Eyebrow } from "./Eyebrow";
import { Reveal } from "./Reveal";

export function Intro() {
  return (
    <section id="what" className="hairline scroll-mt-16 bg-white py-24 sm:py-32">
      <Reveal>
        <Container className="grid gap-10 lg:grid-cols-[240px_1fr] lg:gap-14">
          <div className="pt-1.5">
            <Eyebrow>Introducing Cairn</Eyebrow>
          </div>

          <div className="max-w-[820px] space-y-7 text-[20px] leading-[1.45] text-ink/85">
            <p data-reveal>
              Ask your AI to pull a report off a website and it starts from nothing.
              It opens the page, reads the whole thing, works out where to click, and
              slowly gets there. Tomorrow you ask for the same report. It does the
              same work again. Same reading, same guessing, same wait, same bill.
            </p>
            <p data-reveal>
              Cairn gives it a memory of the trail. The first walk is slow, because
              nobody has been there yet. Cairn leaves markers along the way. Every
              walk after that follows the markers instead of the map. And when the
              path moves, Cairn moves the marker and keeps going.
            </p>
          </div>
        </Container>
      </Reveal>
    </section>
  );
}
