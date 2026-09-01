export function Eyebrow({ children }: { children: string }) {
  return (
    <p className="text-[16px] font-medium text-moss" data-reveal>
      {children} <span aria-hidden className="opacity-50">›</span>
    </p>
  );
}
