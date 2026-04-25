"use client";

import type { Agent, AgentStatus, TrunkCommit } from "@/lib/mockData";

const ROW_H = 40;
const TRUNK_PAD_TOP = 70;
const TRUNK_PAD_BOTTOM = 70;
const LEFT_GUTTER = 60;
const RIGHT_PAD = 60;
const TIMELINE_PX = 1080;
const REACH = 28;

const STATUS_COLOR: Record<AgentStatus, string> = {
  running: "var(--st-running)",
  pending: "var(--st-pending)",
  done: "var(--st-done)",
  failed: "var(--st-failed)",
  merging: "var(--st-merging)",
  merged: "var(--st-merged)",
};

function timeToX(t: number, totalMins: number) {
  return LEFT_GUTTER + (t / totalMins) * TIMELINE_PX;
}

interface LeafClusterProps {
  cx: number;
  cy: number;
  dir: number;
  color: string;
  status: AgentStatus;
  onClick: () => void;
  isActive: boolean;
}

function LeafCluster({ cx, cy, dir, color, status, onClick, isActive }: LeafClusterProps) {
  const tilt = dir < 0 ? -32 : 32;
  const pulsing = status === "running";
  const scale = isActive ? 1.25 : 1;
  return (
    <g
      transform={`translate(${cx}, ${cy}) scale(${scale})`}
      style={{ pointerEvents: "auto", cursor: "pointer" }}
      onClick={onClick}
    >
      {pulsing && (
        <circle r="22" fill="none" stroke={color} strokeWidth="1" opacity="0.4">
          <animate attributeName="r" values="16;28;16" dur="2.8s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.5;0;0.5" dur="2.8s" repeatCount="indefinite" />
        </circle>
      )}
      <line
        x1={dir < 0 ? -5 : 5}
        y1={dir < 0 ? 6 : -6}
        x2="0"
        y2="0"
        stroke="var(--bark)"
        strokeWidth="1.4"
        opacity="0.7"
        strokeLinecap="round"
      />
      <path
        d="M 0 -13 C 11 -13, 15 -3, 13 6 C 11 11, 5 14, -1 12 C -9 10, -14 3, -13 -4 C -11 -11, -6 -14, 0 -13 Z"
        fill={color}
        opacity={status === "pending" ? 0.35 : 0.6}
        transform={`rotate(${tilt - 22})`}
      />
      <path
        d="M 0 -11 C 9 -11, 13 -3, 11 5 C 10 10, 4 12, -1 10 C -8 8, -12 2, -11 -4 C -10 -9, -5 -12, 0 -11 Z"
        fill={color}
        opacity={status === "pending" ? 0.5 : 0.85}
        transform={`rotate(${tilt})`}
      />
      <path
        d="M 0 -10 C 8 -10, 12 -3, 11 4 C 9 9, 4 11, 0 10 C -7 9, -11 2, -10 -3 C -9 -8, -4 -10, 0 -10 Z"
        fill={color}
        opacity={status === "pending" ? 0.65 : 1}
        transform={`rotate(${tilt + 18})`}
      />
      <path
        d="M -5 -3 L 6 5"
        stroke="var(--bg)"
        strokeWidth="0.8"
        opacity="0.4"
        transform={`rotate(${tilt + 18})`}
      />
      <path
        d="M -5 -3 L 6 5"
        stroke="var(--bg)"
        strokeWidth="0.6"
        opacity="0.3"
        transform={`rotate(${tilt})`}
      />
    </g>
  );
}

interface Props {
  agents: Agent[];
  trunkCommits: TrunkCommit[];
  totalMins: number;
  now: number;
  activeId: string | null;
  onSelect: (id: string) => void;
}

interface Lane extends Agent {
  y: number;
  above: boolean;
  laneDistance: number;
}

// Greedy lane packing: each agent is placed in the closest free lane on either side
// of the trunk. Tries above at distance 1, then below at distance 1, then above at
// distance 2, etc. Concurrent agents never share a lane; sequential agents (one
// finishes before the next spawns) reuse the same lane for a clean horizontal stripe.
function packLanes(agents: Agent[]) {
  const sorted = [...agents].sort((a, b) => a.spawnedAt - b.spawnedAt);
  const aboveLaneEnd: number[] = [];
  const belowLaneEnd: number[] = [];
  const placement = new Map<string, { above: boolean; distance: number }>();

  const tryPlace = (lanes: number[], distance: number, start: number, end: number) => {
    const idx = distance - 1;
    const free = (lanes[idx] ?? -Infinity) <= start;
    if (free) lanes[idx] = end;
    return free;
  };

  for (const a of sorted) {
    const start = a.spawnedAt;
    const end = a.mergedAt ?? a.endedAt ?? Number.POSITIVE_INFINITY;
    for (let d = 1; d <= 32; d++) {
      if (tryPlace(aboveLaneEnd, d, start, end)) {
        placement.set(a.id, { above: true, distance: d });
        break;
      }
      if (tryPlace(belowLaneEnd, d, start, end)) {
        placement.set(a.id, { above: false, distance: d });
        break;
      }
    }
  }

  return {
    placement,
    aboveCount: aboveLaneEnd.length,
    belowCount: belowLaneEnd.length,
  };
}

export function ForestTimeline({
  agents,
  trunkCommits,
  totalMins,
  now,
  activeId,
  onSelect,
}: Props) {
  const { placement, aboveCount, belowCount } = packLanes(agents);

  const TRUNK_Y = TRUNK_PAD_TOP + Math.max(aboveCount, 1) * ROW_H;

  const lanes: Lane[] = agents.map((a) => {
    const p = placement.get(a.id) ?? { above: true, distance: 1 };
    return {
      ...a,
      y: TRUNK_Y + (p.above ? -p.distance * ROW_H : p.distance * ROW_H),
      above: p.above,
      laneDistance: p.distance,
    };
  });

  const height =
    TRUNK_PAD_TOP +
    Math.max(aboveCount, 1) * ROW_H +
    Math.max(belowCount, 1) * ROW_H +
    TRUNK_PAD_BOTTOM;
  const width = LEFT_GUTTER + TIMELINE_PX + RIGHT_PAD;

  const trunkX0 = timeToX(0, totalMins);
  const trunkX1 = timeToX(now, totalMins);
  const trunkXEnd = timeToX(totalMins, totalMins);

  const branchPath = (a: Lane) => {
    const x0 = timeToX(a.spawnedAt, totalMins);
    const xEnd = timeToX(a.endedAt ?? now, totalMins);
    const xMerge = a.mergedAt != null ? timeToX(a.mergedAt, totalMins) : null;
    const y = a.y;

    // Clamp reach so the curve never overshoots `now` or eats the entire run length.
    const span = (xMerge ?? xEnd) - x0;
    const reach = Math.max(8, Math.min(REACH, span * 0.45));
    const bend = reach * 0.55;

    // Spawn S-curve: trunk -> lane (horizontally tangent at both ends, no overshoot).
    let d = `M ${x0} ${TRUNK_Y} `;
    d += `C ${x0 + bend} ${TRUNK_Y}, ${x0 + reach - bend} ${y}, ${x0 + reach} ${y} `;

    const runEnd = xMerge !== null ? Math.max(x0 + reach, xMerge - reach) : xEnd;
    if (runEnd > x0 + reach) {
      d += `L ${runEnd} ${y} `;
    }

    if (xMerge !== null) {
      // Merge S-curve: lane -> trunk (mirror of spawn).
      d += `C ${runEnd + bend} ${y}, ${xMerge - bend} ${TRUNK_Y}, ${xMerge} ${TRUNK_Y}`;
    }
    return d;
  };

  const Tip = ({ a }: { a: Lane }) => {
    const x = timeToX(a.endedAt ?? now, totalMins);
    const y = a.y;
    const color = STATUS_COLOR[a.status];
    const dir = a.above ? -1 : 1;
    const handleClick = () => onSelect(a.id);

    if (a.status === "running" || a.status === "pending") {
      return (
        <LeafCluster
          cx={x}
          cy={y}
          dir={dir}
          color={color}
          status={a.status}
          onClick={handleClick}
          isActive={a.id === activeId}
        />
      );
    }
    if (a.status === "done") {
      return (
        <g
          transform={`translate(${x}, ${y})`}
          style={{ pointerEvents: "auto", cursor: "pointer" }}
          onClick={handleClick}
        >
          <circle r="6" fill={color} />
          <circle r="6" fill="none" stroke="var(--bg)" strokeWidth="1.5" opacity="0.4" />
          <circle cx="-1.6" cy="-1.6" r="1.4" fill="var(--bg)" opacity="0.3" />
        </g>
      );
    }
    if (a.status === "failed") {
      return (
        <g
          transform={`translate(${x}, ${y})`}
          style={{ pointerEvents: "auto", cursor: "pointer" }}
          onClick={handleClick}
        >
          <path
            d="M 0 -7 C 6 -7, 9 -2, 8 3 C 7 6, 3 8, -1 7 C -5 6, -8 1, -7 -3 C -6 -6, -3 -8, 0 -7 Z"
            fill="none"
            stroke={color}
            strokeWidth="1.2"
            strokeDasharray="2 2"
            transform={`rotate(${dir < 0 ? -25 : 25})`}
          />
          <line x1="-3" y1="-3" x2="3" y2="3" stroke={color} strokeWidth="1.5" />
          <line x1="-3" y1="3" x2="3" y2="-3" stroke={color} strokeWidth="1.5" />
        </g>
      );
    }
    if (a.status === "merging") {
      return (
        <g
          transform={`translate(${x}, ${y})`}
          style={{ pointerEvents: "auto", cursor: "pointer" }}
          onClick={handleClick}
        >
          <circle r="7" fill="var(--bg)" stroke={color} strokeWidth="1.5">
            <animate attributeName="r" values="7;10;7" dur="1.6s" repeatCount="indefinite" />
          </circle>
          <circle r="3" fill={color} />
        </g>
      );
    }
    return null;
  };

  return (
    <div className="forest">
      <div className="forest-canvas" style={{ width: "100%", position: "relative" }}>
        <div
          className="forest-time-axis"
          style={{
            marginLeft: `${(LEFT_GUTTER / width) * 100}%`,
            width: `${(TIMELINE_PX / width) * 100}%`,
          }}
        >
          <span>3h ago</span>
          <span>2h ago</span>
          <span>1h ago</span>
          <span>now</span>
        </div>

        <svg
          className="forest-svg"
          width="100%"
          viewBox={`0 0 ${width} ${height}`}
          preserveAspectRatio="xMinYMid meet"
        >
          <defs>
            <linearGradient id="trunk-gradient" x1="0" x2="1" y1="0" y2="0">
              <stop offset="0%" stopColor="var(--bark)" />
              <stop offset="60%" stopColor="var(--bark-light)" />
              <stop offset="100%" stopColor="var(--leaf)" />
            </linearGradient>
            <linearGradient id="trunk-shadow" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="var(--bark-light)" stopOpacity="0.5" />
              <stop offset="100%" stopColor="var(--bark)" stopOpacity="0.9" />
            </linearGradient>
            <pattern
              id="bark-texture"
              patternUnits="userSpaceOnUse"
              width="6"
              height="14"
              patternTransform="rotate(2)"
            >
              <line x1="0" y1="0" x2="0" y2="14" stroke="var(--bg)" strokeWidth="0.4" opacity="0.25" />
              <line x1="3" y1="2" x2="3" y2="12" stroke="var(--bg)" strokeWidth="0.3" opacity="0.18" />
            </pattern>
          </defs>

          {lanes.map((a) => (
            <line
              key={`guide-${a.id}`}
              x1={LEFT_GUTTER}
              x2={LEFT_GUTTER + TIMELINE_PX}
              y1={a.y}
              y2={a.y}
              stroke="var(--line)"
              strokeWidth="1"
              strokeDasharray="2 8"
              opacity="0.4"
            />
          ))}

          <line
            x1={trunkX1}
            x2={trunkX1}
            y1="20"
            y2={height - 30}
            stroke="var(--leaf-light)"
            strokeWidth="1"
            strokeDasharray="3 4"
            opacity="0.35"
          />
          <text
            x={trunkX1 + 6}
            y={height - 30}
            fill="var(--leaf-light)"
            fontFamily="var(--mono)"
            fontSize="9"
            opacity="0.7"
            letterSpacing="1.5"
          >
            NOW
          </text>

          <path
            d={`M ${trunkX0} ${TRUNK_Y - 7} L ${trunkXEnd} ${TRUNK_Y - 4} L ${trunkXEnd} ${TRUNK_Y + 4} L ${trunkX0} ${TRUNK_Y + 7} Z`}
            fill="var(--bark)"
            opacity="0.35"
          />
          <path
            d={`M ${trunkX0} ${TRUNK_Y - 6} L ${trunkX1} ${TRUNK_Y - 4} L ${trunkX1} ${TRUNK_Y + 4} L ${trunkX0} ${TRUNK_Y + 6} Z`}
            fill="url(#trunk-gradient)"
          />
          <path
            d={`M ${trunkX0} ${TRUNK_Y - 6} L ${trunkX1} ${TRUNK_Y - 4} L ${trunkX1} ${TRUNK_Y + 4} L ${trunkX0} ${TRUNK_Y + 6} Z`}
            fill="url(#bark-texture)"
          />

          {trunkCommits.map((c, i) => {
            const x = timeToX(c.at, totalMins);
            return (
              <g key={i} transform={`translate(${x}, ${TRUNK_Y})`}>
                <ellipse
                  cx="0"
                  cy="0"
                  rx="4.5"
                  ry="3.5"
                  fill="var(--bark-light)"
                  stroke="var(--bg)"
                  strokeWidth="0.8"
                />
                <ellipse cx="0" cy="0" rx="2" ry="1.5" fill="var(--bark)" />
                {c.inProgress && (
                  <circle r="6" fill="none" stroke="var(--amber)" strokeWidth="1.2">
                    <animate attributeName="r" values="6;11;6" dur="1.8s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="1;0;1" dur="1.8s" repeatCount="indefinite" />
                  </circle>
                )}
                <text
                  x="0"
                  y="-14"
                  textAnchor="middle"
                  fill="var(--ash)"
                  fontFamily="var(--mono)"
                  fontSize="9"
                  letterSpacing="0.5"
                >
                  {c.sha}
                </text>
              </g>
            );
          })}

          {lanes.map((a) => {
            const isActive = a.id === activeId;
            const color = STATUS_COLOR[a.status];
            const isMuted = a.status === "merged" || a.status === "failed";
            const baseOpacity = isActive ? 1 : isMuted ? 0.4 : 0.85;
            return (
              <g key={a.id}>
                <path
                  d={branchPath(a)}
                  fill="none"
                  stroke="var(--bark)"
                  strokeWidth={isActive ? 4 : 3}
                  strokeLinecap="round"
                  opacity={baseOpacity * 0.5}
                />
                <path
                  className="branch"
                  d={branchPath(a)}
                  fill="none"
                  stroke={color}
                  strokeWidth={isActive ? 2.5 : 1.75}
                  strokeLinecap="round"
                  opacity={baseOpacity}
                  strokeDasharray={a.status === "pending" ? "3 4" : undefined}
                  onClick={() => onSelect(a.id)}
                />
                <g transform={`translate(${timeToX(a.spawnedAt, totalMins)}, ${TRUNK_Y})`}>
                  <ellipse
                    rx="3"
                    ry="2"
                    fill={color}
                    opacity="0.9"
                    transform={`rotate(${a.above ? -45 : 45})`}
                  />
                </g>
              </g>
            );
          })}

          {lanes.map((a) => (
            <Tip key={`tip-${a.id}`} a={a} />
          ))}

          <text
            x={LEFT_GUTTER - 14}
            y={TRUNK_Y + 4}
            textAnchor="end"
            fill="var(--sage)"
            fontFamily="var(--serif)"
            fontStyle="italic"
            fontSize="15"
          >
            main
          </text>
          <text
            x={LEFT_GUTTER - 14}
            y={TRUNK_Y + 18}
            textAnchor="end"
            fill="var(--ash-2)"
            fontFamily="var(--mono)"
            fontSize="9"
            letterSpacing="1"
          >
            TRUNK
          </text>

          {lanes.map((a) => {
            const sx = timeToX(a.spawnedAt, totalMins);
            const xEnd = timeToX(a.endedAt ?? now, totalMins);
            const xMerge = a.mergedAt != null ? timeToX(a.mergedAt, totalMins) : null;
            const span = (xMerge ?? xEnd) - sx;
            const reach = Math.max(8, Math.min(REACH, span * 0.45));
            const labelX = sx + reach + 6;
            const labelYName = a.y - 18;
            const labelYPort = a.y - 6;
            return (
              <g
                key={`label-${a.id}`}
                style={{ pointerEvents: "auto", cursor: "pointer" }}
                onClick={() => onSelect(a.id)}
              >
                <text
                  x={labelX}
                  y={labelYName}
                  textAnchor="start"
                  fill={a.id === activeId ? "var(--leaf-light)" : "var(--parchment)"}
                  fontFamily="var(--mono)"
                  fontSize="11"
                  fontWeight={a.id === activeId ? 600 : 400}
                  opacity={a.status === "merged" ? 0.5 : 1}
                >
                  {a.name}
                </text>
                <text
                  x={labelX}
                  y={labelYPort}
                  textAnchor="start"
                  fill="var(--ash-2)"
                  fontFamily="var(--mono)"
                  fontSize="9"
                  letterSpacing="0.5"
                  opacity={a.status === "merged" ? 0.5 : 1}
                >
                  :{a.portBase}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
