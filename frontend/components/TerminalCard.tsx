import type { ReactNode } from "react";

/** A light terminal, so it belongs on the page instead of punching a hole in it. */
export function TerminalCard({
  title,
  children,
  className = "",
}: {
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`surface-raised overflow-hidden rounded-xl bg-white ${className}`}
    >
      <div className="flex items-center gap-2 border-b border-black/6 bg-soft px-5 py-3.5">
        <span className="h-[9px] w-[9px] rounded-full bg-black/12" />
        <span className="h-[9px] w-[9px] rounded-full bg-black/12" />
        <span className="h-[9px] w-[9px] rounded-full bg-black/12" />
        <span className="ml-3 font-mono text-[12.5px] text-faint">{title}</span>
      </div>
      <div className="px-6 py-6 font-mono text-[13.5px] leading-[2] text-ink/80 sm:px-8">
        {children}
      </div>
    </div>
  );
}

export function TPrompt({ children }: { children: ReactNode }) {
  return (
    <p className="font-medium text-ink">
      <span className="mr-2.5 select-none text-faint">›</span>
      {children}
    </p>
  );
}

export function TDim({ children }: { children: ReactNode }) {
  return <p className="text-faint">{children}</p>;
}

export function TOk({ children }: { children: ReactNode }) {
  return (
    <p className="text-moss">
      <span className="mr-2.5 select-none">✓</span>
      {children}
    </p>
  );
}

export function TWarn({ children }: { children: ReactNode }) {
  return (
    <p className="text-[#b0703a]">
      <span className="mr-2.5 select-none">!</span>
      {children}
    </p>
  );
}
