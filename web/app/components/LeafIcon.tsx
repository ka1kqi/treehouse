interface Props {
  size?: number;
  color?: string;
}

export function LeafIcon({ size = 14, color = "currentColor" }: Props) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <path
        d="M 8 2 C 12 2, 14 5, 14 9 C 14 12, 11 14, 8 14 C 5 14, 2 12, 2 9 C 2 5, 4 2, 8 2 Z"
        fill={color}
        opacity="0.85"
      />
      <path d="M 8 2 L 8 14" stroke="var(--bg)" strokeWidth="0.6" opacity="0.4" />
    </svg>
  );
}
