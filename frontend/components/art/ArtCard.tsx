import type { ReactNode } from "react";

/** Square-ish card that crops whatever product UI is laid inside it. */
export function ArtCard({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`surface relative aspect-[1000/860] overflow-hidden rounded-xl bg-soft ${className}`}
    >
      {children}
    </div>
  );
}
