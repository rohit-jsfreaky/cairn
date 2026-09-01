"use client";

import { useRef, type ReactNode } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(useGSAP, ScrollTrigger, SplitText);

/** A heading whose words rise out of the line when it scrolls into view. */
export function SplitHeading({
  children,
  className = "",
  level = 2,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  level?: 1 | 2;
  delay?: number;
}) {
  const ref = useRef<HTMLHeadingElement>(null);

  useGSAP(
    () => {
      const el = ref.current;
      if (!el) return;

      const split = SplitText.create(el, {
        type: "lines,words",
        mask: "lines",
        aria: "auto",
        autoSplit: true,
        onSplit: (self) =>
          gsap.from(self.words, {
            yPercent: 115,
            autoAlpha: 0,
            duration: 0.95,
            ease: "power3.out",
            stagger: 0.035,
            delay,
            scrollTrigger: { trigger: el, start: "top 88%", once: true },
          }),
      });

      return () => {
        split.revert();
      };
    },
    { scope: ref },
  );

  const Tag = level === 1 ? "h1" : "h2";
  return (
    <Tag ref={ref} className={className}>
      {children}
    </Tag>
  );
}
