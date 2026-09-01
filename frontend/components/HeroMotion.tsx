"use client";

import { useRef, type ReactNode } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(useGSAP, ScrollTrigger);

/** The opening beat: the words arrive, then the terminal rises into place. */
export function HeroMotion({ children }: { children: ReactNode }) {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const lines = gsap.utils.toArray<HTMLElement>("[data-hero-line]");
      const terminal = gsap.utils.toArray<HTMLElement>("[data-hero-terminal]");
      const photo = gsap.utils.toArray<HTMLElement>("[data-hero-photo]");

      gsap.set(lines, { autoAlpha: 0, y: 26 });
      gsap.set(terminal, { autoAlpha: 0, y: 56 });

      gsap
        .timeline({ defaults: { ease: "power3.out" } })
        .to(lines, { autoAlpha: 1, y: 0, duration: 0.9, stagger: 0.09 })
        .to(terminal, { autoAlpha: 1, y: 0, duration: 1.2 }, "-=0.55");

      // the photo drifts slower than the page, so the card feels deep
      gsap.to(photo, {
        yPercent: 8,
        ease: "none",
        scrollTrigger: {
          trigger: root.current,
          start: "top top",
          end: "bottom top",
          scrub: true,
        },
      });
    },
    { scope: root },
  );

  return <div ref={root}>{children}</div>;
}
