import Image from "next/image";
import { HeroMotion } from "./HeroMotion";
import { HeroTerminal } from "./HeroTerminal";
import { SiteNav } from "./SiteNav";

export function Hero() {
  return (
    <div className="p-2 pb-0 md:p-4 md:pb-0">
      <HeroMotion>
        <section className="relative overflow-hidden rounded-2xl bg-[#cfe8f8] shadow-[0_2px_6px_rgb(10_11_12/0.04),0_24px_60px_-32px_rgb(10_11_12/0.24)] md:rounded-3xl">
          <div className="absolute inset-0 scale-110" data-hero-photo>
            <Image
              src="/art/hero-sky.png"
              alt=""
              fill
              priority
              sizes="100vw"
              className="object-cover object-center"
            />
          </div>

          <div className="relative">
            <SiteNav />

            <div className="mx-auto max-w-[1100px] px-6 pt-20 pb-14 text-center sm:pt-24">
              <p className="text-[15px] font-medium text-ink/45" data-hero-line>
                Works inside Claude Code, Cursor and Codex
              </p>

              <h1
                className="mt-6 font-display text-[clamp(34px,5vw,58px)] font-medium leading-[1.08] tracking-[-0.01em] text-ink"
                data-hero-line
              >
                Your AI can use websites.
                <br />
                It just cannot remember how.
              </h1>

              <p
                className="mx-auto mt-7 max-w-[620px] text-[20px] leading-[1.45] text-ink/65"
                data-hero-line
              >
                Cairn is the part that remembers. It learns a site once, then walks
                it again in a single step.
              </p>

              <div className="mt-10 flex items-center justify-center gap-3" data-hero-line>
                <a
                  href="#install"
                  className="rounded-full bg-ink px-6 py-3 text-[15px] font-medium text-white transition-opacity hover:opacity-85"
                >
                  Install Cairn
                </a>
                <a
                  href="#what"
                  className="rounded-full bg-white/70 px-6 py-3 text-[15px] font-medium text-ink/75 backdrop-blur-sm transition-colors hover:bg-white hover:text-ink"
                >
                  See what it does
                </a>
              </div>
            </div>

            <div className="mx-auto mb-[-96px] max-w-[1080px] px-6" data-hero-terminal>
              <HeroTerminal />
            </div>
          </div>
        </section>
      </HeroMotion>
    </div>
  );
}
