import Image from "next/image";
import { Container } from "./Container";
import { CopyCommand } from "./CopyCommand";
import { SplitHeading } from "./SplitHeading";

export function Closing() {
  return (
    <div className="p-2 md:p-4" id="install">
      <section className="relative scroll-mt-16 overflow-hidden rounded-2xl bg-white shadow-[0_2px_6px_rgb(10_11_12/0.04),0_24px_60px_-32px_rgb(10_11_12/0.20)] md:rounded-3xl">
        <Image
          src="/art/band-glow.png"
          alt=""
          fill
          sizes="100vw"
          className="object-cover object-bottom"
        />

        {/* The fine dot grid, drawn crisply instead of baked into the image,
            and masked so it only appears inside the glow. */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage:
              "radial-gradient(circle, rgb(255 255 255 / 0.55) 1px, transparent 1.2px)",
            backgroundSize: "16px 16px",
            maskImage:
              "radial-gradient(ellipse 62% 95% at 50% 108%, #000 10%, transparent 72%)",
            WebkitMaskImage:
              "radial-gradient(ellipse 62% 95% at 50% 108%, #000 10%, transparent 72%)",
          }}
        />

        <Container className="relative py-28 text-center sm:py-36">
          <p className="font-mono text-[12.5px] tracking-[0.08em] text-ink/55">
            IN THE EDITOR YOU ALREADY USE
          </p>

          <SplitHeading className="mx-auto mt-7 max-w-[860px] font-display text-[clamp(30px,3.8vw,50px)] font-medium leading-[1.1] text-ink">
            Leave a marker on the trail.
          </SplitHeading>

          <p className="mx-auto mt-6 max-w-[540px] text-[19px] leading-[1.5] text-ink/65">
            Your AI stops starting over on every site it visits.
          </p>

          <div className="mt-11 flex justify-center">
            <CopyCommand />
          </div>

          <p className="mx-auto mt-6 max-w-[540px] text-[15px] leading-[1.5] text-ink/50">
            Then three lines in the{" "}
            <a
              href="https://github.com/rohit-jsfreaky/cairn#install"
              className="underline decoration-ink/25 underline-offset-4 transition-colors hover:text-ink/75"
            >
              README
            </a>
            . Nothing is on PyPI yet, so Cairn installs from the clone.
          </p>
        </Container>
      </section>
    </div>
  );
}
