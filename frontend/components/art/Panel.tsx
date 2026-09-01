import type { ReactNode } from "react";

/** A piece of Cairn's own interface. Used large and cropped, never shrunk to fit. */
export function Panel({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`surface-raised overflow-hidden rounded-lg bg-white ${className}`}
    >
      {title ? (
        <div className="border-b border-black/6 px-5 py-3.5 font-mono text-[12.5px] text-faint">
          {title}
        </div>
      ) : null}
      {children}
    </div>
  );
}
