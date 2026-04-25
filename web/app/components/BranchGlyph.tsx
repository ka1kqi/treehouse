interface Props {
  size?: number;
}

export function BranchGlyph({ size = 12 }: Props) {
  return (
    <svg width={size} height={size} viewBox="0 0 12 12" fill="none">
      <circle cx="3" cy="2.5" r="1.5" fill="currentColor" />
      <circle cx="3" cy="9.5" r="1.5" fill="currentColor" />
      <circle cx="9" cy="6" r="1.5" fill="currentColor" />
      <path d="M 3 4 L 3 8 M 3 6 Q 6 6 9 6" stroke="currentColor" strokeWidth="1" fill="none" />
    </svg>
  );
}
