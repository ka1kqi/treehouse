"use client";

import { useEffect, useRef } from "react";

const GRID_STEP = 14;
const CHAR_IDLE = "·";
const CHAR_ACTIVE = "•";
const CHAR_MERGE = "○";
const ACCENT_RGB = "127, 214, 168";
const FG_RGB = "232, 232, 232";

const NUM_AGENTS = 5;
const AGENT_SPEED = 28;
const ACTIVATION_RADIUS = GRID_STEP * 1.6;
const MOUSE_RADIUS = 120;
const TRAIL_HALF_LIFE = 0.7;
const MERGE_WINDOW_MS = 220;
const FLASH_DURATION_MS = 220;

type Cell = {
  px: number;
  py: number;
  activation: number;
  flashUntil: number;
  lastTouchedBy: number;
  lastTouchedAt: number;
};

type Agent = {
  id: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
};

export default function DotField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvasEl = canvasRef.current;
    const wrapEl = wrapRef.current;
    if (!canvasEl || !wrapEl) return;
    const ctx2d = canvasEl.getContext("2d");
    if (!ctx2d) return;
    const canvas: HTMLCanvasElement = canvasEl;
    const wrap: HTMLDivElement = wrapEl;
    const ctx: CanvasRenderingContext2D = ctx2d;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let cells: Cell[] = [];
    let width = 0;
    let height = 0;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    let agents: Agent[] = [];
    const mouse = { x: -9999, y: -9999, active: false };
    let lastTime = performance.now();
    let raf = 0;

    function setupGrid() {
      const rect = wrap.getBoundingClientRect();
      width = Math.max(1, Math.floor(rect.width));
      height = Math.max(1, Math.floor(rect.height));
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);

      const cols = Math.floor(width / GRID_STEP);
      const rows = Math.floor(height / GRID_STEP);
      const offsetX = (width - cols * GRID_STEP) / 2 + GRID_STEP / 2;
      const offsetY = (height - rows * GRID_STEP) / 2 + GRID_STEP / 2;

      cells = [];
      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
          cells.push({
            px: offsetX + x * GRID_STEP,
            py: offsetY + y * GRID_STEP,
            activation: 0,
            flashUntil: 0,
            lastTouchedBy: -1,
            lastTouchedAt: 0,
          });
        }
      }

      if (agents.length === 0) {
        for (let i = 0; i < NUM_AGENTS; i++) {
          const angle = (i / NUM_AGENTS) * Math.PI * 2 + Math.random() * 0.4;
          agents.push({
            id: i,
            x: width * (0.3 + 0.4 * Math.random()),
            y: height * (0.3 + 0.4 * Math.random()),
            vx: Math.cos(angle) * AGENT_SPEED,
            vy: Math.sin(angle) * AGENT_SPEED,
          });
        }
      } else {
        for (const a of agents) {
          if (a.x < 0 || a.x > width) a.x = width / 2;
          if (a.y < 0 || a.y > height) a.y = height / 2;
        }
      }
    }

    function activateNearbyCells(agent: Agent, now: number) {
      for (const cell of cells) {
        const dx = cell.px - agent.x;
        const dy = cell.py - agent.y;
        const distSq = dx * dx + dy * dy;
        if (distSq > ACTIVATION_RADIUS * ACTIVATION_RADIUS) continue;
        const dist = Math.sqrt(distSq);
        const strength = 1 - dist / ACTIVATION_RADIUS;

        if (
          cell.lastTouchedBy !== -1 &&
          cell.lastTouchedBy !== agent.id &&
          now - cell.lastTouchedAt < MERGE_WINDOW_MS
        ) {
          cell.flashUntil = now + FLASH_DURATION_MS;
        }

        if (cell.activation < strength) cell.activation = strength;
        cell.lastTouchedBy = agent.id;
        cell.lastTouchedAt = now;
      }
    }

    function update(dt: number, now: number) {
      for (const agent of agents) {
        if (mouse.active) {
          const dx = agent.x - mouse.x;
          const dy = agent.y - mouse.y;
          const distSq = dx * dx + dy * dy;
          if (distSq < 180 * 180 && distSq > 1) {
            const dist = Math.sqrt(distSq);
            const force = Math.min(80, 6000 / distSq);
            agent.vx += (dx / dist) * force * dt;
            agent.vy += (dy / dist) * force * dt;
          }
        }

        const speed = Math.hypot(agent.vx, agent.vy);
        if (speed > 0) {
          agent.vx = (agent.vx / speed) * AGENT_SPEED;
          agent.vy = (agent.vy / speed) * AGENT_SPEED;
        }

        agent.x += agent.vx * dt;
        agent.y += agent.vy * dt;

        const margin = 20;
        if (agent.x < -margin) agent.x = width + margin;
        if (agent.x > width + margin) agent.x = -margin;
        if (agent.y < -margin) agent.y = height + margin;
        if (agent.y > height + margin) agent.y = -margin;

        activateNearbyCells(agent, now);
      }

      const decay = Math.exp(-dt / TRAIL_HALF_LIFE);
      for (const cell of cells) cell.activation *= decay;
    }

    function draw(now: number) {
      ctx.clearRect(0, 0, width, height);
      ctx.font =
        "11px ui-monospace, 'JetBrains Mono', SFMono-Regular, Menlo, monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      for (const cell of cells) {
        let mouseBoost = 0;
        if (mouse.active) {
          const dx = cell.px - mouse.x;
          const dy = cell.py - mouse.y;
          const dist = Math.hypot(dx, dy);
          if (dist < MOUSE_RADIUS) {
            mouseBoost = (1 + Math.cos((Math.PI * dist) / MOUSE_RADIUS)) / 2;
          }
        }

        const total = Math.min(1, cell.activation + mouseBoost * 0.85);
        let char = CHAR_IDLE;
        let opacity = 0.18;
        let rgb = FG_RGB;

        if (cell.flashUntil > now) {
          char = CHAR_MERGE;
          opacity = 1;
          rgb = ACCENT_RGB;
        } else if (total > 0.7) {
          char = CHAR_MERGE;
          opacity = 0.55 + total * 0.35;
        } else if (total > 0.28) {
          char = CHAR_ACTIVE;
          opacity = 0.4 + total * 0.4;
        } else if (total > 0) {
          char = CHAR_IDLE;
          opacity = 0.2 + total * 0.4;
        }

        ctx.fillStyle = `rgba(${rgb}, ${opacity})`;
        ctx.fillText(char, cell.px, cell.py);
      }
    }

    function frame(now: number) {
      const dt = Math.min(0.05, (now - lastTime) / 1000);
      lastTime = now;
      update(dt, now);
      draw(now);
      raf = requestAnimationFrame(frame);
    }

    setupGrid();

    if (reduced) {
      draw(performance.now());
    } else {
      lastTime = performance.now();
      raf = requestAnimationFrame(frame);
    }

    const ro = new ResizeObserver(() => {
      cancelAnimationFrame(raf);
      setupGrid();
      lastTime = performance.now();
      if (reduced) draw(performance.now());
      else raf = requestAnimationFrame(frame);
    });
    ro.observe(wrap);

    function onPointerMove(e: PointerEvent) {
      const rect = canvas.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;
      mouse.active = true;
    }
    function onPointerLeave() {
      mouse.active = false;
      mouse.x = -9999;
      mouse.y = -9999;
    }

    wrap.addEventListener("pointermove", onPointerMove);
    wrap.addEventListener("pointerleave", onPointerLeave);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      wrap.removeEventListener("pointermove", onPointerMove);
      wrap.removeEventListener("pointerleave", onPointerLeave);
    };
  }, []);

  return (
    <div ref={wrapRef} className="absolute inset-0">
      <canvas ref={canvasRef} className="block h-full w-full" />
    </div>
  );
}
