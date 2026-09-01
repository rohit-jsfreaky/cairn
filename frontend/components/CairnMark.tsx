/** The Cairn mark: three trail stones, largest at the base. Inherits currentColor. */
export function CairnMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden className={className}>
      <ellipse cx="12" cy="3.42" rx="5.45" ry="3.42" />
      <ellipse cx="12" cy="11.36" rx="8.13" ry="3.69" />
      <ellipse cx="12" cy="19.74" rx="10.69" ry="4.26" />
    </svg>
  );
}
