import { ImageResponse } from "next/og";

export const alt =
  "Treehouse — Parallel runtime isolation for multi-agent coding";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const FONT_REGULAR =
  "https://raw.githubusercontent.com/JetBrains/JetBrainsMono/master/fonts/ttf/JetBrainsMono-Regular.ttf";
const FONT_MEDIUM =
  "https://raw.githubusercontent.com/JetBrains/JetBrainsMono/master/fonts/ttf/JetBrainsMono-Medium.ttf";

async function loadFont(url: string): Promise<ArrayBuffer | null> {
  try {
    const res = await fetch(url, { cache: "force-cache" });
    if (!res.ok) return null;
    return await res.arrayBuffer();
  } catch {
    return null;
  }
}

// Deterministic merge dots — placed off the headline so they read as field texture
// rather than decoration. Coordinates in the 1200×630 frame.
const MERGE_DOTS: { x: number; y: number; opacity?: number }[] = [
  { x: 156, y: 132 },
  { x: 1024, y: 182, opacity: 0.85 },
  { x: 248, y: 504 },
  { x: 920, y: 528, opacity: 0.7 },
  { x: 78, y: 312, opacity: 0.6 },
  { x: 1132, y: 372 },
];

export default async function Image() {
  const [regular, medium] = await Promise.all([
    loadFont(FONT_REGULAR),
    loadFont(FONT_MEDIUM),
  ]);

  const fonts =
    regular && medium
      ? [
          {
            name: "JetBrains Mono",
            data: regular,
            weight: 400 as const,
            style: "normal" as const,
          },
          {
            name: "JetBrains Mono",
            data: medium,
            weight: 500 as const,
            style: "normal" as const,
          },
        ]
      : undefined;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px 80px",
          background: "#0a0a0a",
          color: "#e8e8e8",
          fontFamily: "JetBrains Mono, monospace",
          position: "relative",
        }}
      >
        {/* Background dot grid — radial-gradient pattern, 14px lattice */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage:
              "radial-gradient(circle, rgba(232,232,232,0.18) 1px, transparent 1.4px)",
            backgroundSize: "14px 14px",
            backgroundPosition: "7px 7px",
          }}
        />

        {/* Accent merge dots */}
        {MERGE_DOTS.map((d, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              left: d.x - 7,
              top: d.y - 7,
              width: 14,
              height: 14,
              border: "1.5px solid #7fd6a8",
              borderRadius: 999,
              opacity: d.opacity ?? 1,
              display: "flex",
            }}
          />
        ))}

        {/* Top row: wordmark */}
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            gap: 18,
            zIndex: 1,
          }}
        >
          <span
            style={{
              fontSize: 22,
              fontWeight: 500,
              letterSpacing: "0.22em",
              color: "#e8e8e8",
            }}
          >
            TREEHOUSE
          </span>
          <span
            style={{
              fontSize: 16,
              letterSpacing: "0.22em",
              color: "rgba(232,232,232,0.45)",
            }}
          >
            V0.1
          </span>
        </div>

        {/* Headline */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            zIndex: 1,
          }}
        >
          <span
            style={{
              fontSize: 76,
              fontWeight: 400,
              lineHeight: 1.06,
              letterSpacing: "-0.025em",
              color: "#e8e8e8",
            }}
          >
            Parallel runtime isolation
          </span>
          <span
            style={{
              fontSize: 76,
              fontWeight: 400,
              lineHeight: 1.06,
              letterSpacing: "-0.025em",
              color: "#e8e8e8",
            }}
          >
            for multi-agent coding.
          </span>
          <span
            style={{
              marginTop: 26,
              fontSize: 22,
              lineHeight: 1.5,
              color: "rgba(232,232,232,0.6)",
              maxWidth: 880,
            }}
          >
            An orchestrator decomposes a task into parallel agents, each in
            an isolated worktree and Docker project — then merges them back.
          </span>
        </div>

        {/* Bottom row: tagline */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            zIndex: 1,
          }}
        >
          <span
            style={{
              fontSize: 14,
              letterSpacing: "0.22em",
              color: "rgba(232,232,232,0.45)",
            }}
          >
            CLI HARNESS · PER-AGENT SANDBOXES
          </span>
          <span
            style={{
              fontSize: 14,
              letterSpacing: "0.22em",
              color: "#7fd6a8",
            }}
          >
            ○ MERGE
          </span>
        </div>
      </div>
    ),
    {
      ...size,
      fonts,
    }
  );
}
