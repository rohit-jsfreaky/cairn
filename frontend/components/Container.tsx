import type { ReactNode } from "react";

/** Wide, but not so wide that a two column split pulls apart. */
export function Container({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`mx-auto w-full max-w-[1280px] px-6 ${className}`}>{children}</div>
  );
}
