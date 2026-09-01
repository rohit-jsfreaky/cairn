import { CONTROL_TILES } from "./art/ControlTiles";
import { Container } from "./Container";
import { Eyebrow } from "./Eyebrow";
import { Reveal } from "./Reveal";
import { SplitHeading } from "./SplitHeading";

export function Control() {
  return (
    <section className="hairline bg-mist py-24 sm:py-32">
      <Reveal stagger={0.1}>
        <Container className="text-center">
          <div className="flex justify-center">
            <Eyebrow>Yours, on your terms</Eyebrow>
          </div>

          <SplitHeading className="mx-auto mt-6 max-w-[760px] font-display text-[clamp(28px,3.4vw,44px)] font-medium leading-[1.1] text-ink">
            It runs on your machine.
          </SplitHeading>

          <div className="mt-16 grid gap-6 text-left sm:grid-cols-2 lg:grid-cols-4">
            {CONTROL_TILES.map((tile) => (
              <div key={tile.lead} data-reveal>
                {tile.art}
                <p className="mt-5 text-[16px] font-medium text-ink">{tile.lead}</p>
                <p className="mt-2.5 text-[15px] leading-[1.55] text-muted">{tile.body}</p>
              </div>
            ))}
          </div>
        </Container>
      </Reveal>
    </section>
  );
}
