/** A soft colour form that sits behind the UI, the way the reference site does it. */
export function Blob({ className = "", color }: { className?: string; color: string }) {
  return (
    <div
      aria-hidden
      className={`pointer-events-none absolute rounded-full blur-[64px] ${className}`}
      style={{ background: color }}
    />
  );
}
