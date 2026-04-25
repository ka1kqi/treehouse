import DotField from "./components/DotField";
import InstallButton from "./components/InstallButton";

const COMMANDS: [string, string][] = [
  ["treehouse init", "initialize in the current repo"],
  ["treehouse orchestrate \"<task>\"", "decompose a task and spawn agents in parallel"],
  ["treehouse spawn <name> \"<task>\"", "create workspace + launch a single agent"],
  ["treehouse list", "list all agents and status"],
  ["treehouse stop <name>", "stop a running agent"],
  ["treehouse merge <name>", "merge agent's branch back to main"],
  ["treehouse destroy <name>", "tear down workspace + containers"],
  ["treehouse dashboard", "launch the TUI dashboard"],
];

export default function Page() {
  return (
    <main className="min-h-screen">
      {/* HERO */}
      <section className="relative h-[100svh] min-h-[640px] w-full overflow-hidden">
        <DotField />

        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center px-6">
          <div className="headline-blend mx-auto flex max-w-3xl flex-col items-center text-center">
            <div className="mb-6 text-[11px] tracking-wider2 text-fg/80">
              TREEHOUSE / V0.1
            </div>
            <h1 className="text-balance text-[clamp(28px,5vw,52px)] font-light leading-[1.08] tracking-tight">
              Parallel runtime isolation
              <br />
              for multi-agent coding.
            </h1>
            <p className="mt-6 max-w-xl text-pretty text-[13px] leading-relaxed text-fg/70 sm:text-sm">
              An orchestrator decomposes a task into parallel agents, each in
              an isolated worktree and Docker project — then merges their work
              back with AI-assisted conflict resolution.
            </p>
          </div>

          <div className="pointer-events-auto mt-10 flex flex-wrap items-center justify-center gap-3">
            <InstallButton />
            <a
              href="https://github.com/ka1kqi/treehouse"
              target="_blank"
              rel="noreferrer noopener"
              className="focus-ring border border-hairline px-4 py-2 text-[13px] tracking-wider2 text-fg transition-colors hover:border-accent hover:text-accent"
            >
              github <span aria-hidden>↗</span>
            </a>
          </div>

          <div className="pointer-events-none absolute bottom-6 left-1/2 -translate-x-1/2 text-[10px] tracking-wider2 text-fg/40">
            CLI HARNESS · PER-AGENT SANDBOXES
          </div>
        </div>
      </section>

      {/* PROBLEM */}
      <section className="border-t border-hairline">
        <div className="mx-auto max-w-page px-6 py-24 sm:py-32">
          <div className="mb-8 text-[10px] tracking-wider2 text-muted">
            01 — THE PROBLEM
          </div>
          <p className="text-balance text-[clamp(22px,3.4vw,36px)] font-light leading-[1.2] tracking-tight text-fg">
            Multiple agents on one repo collide on ports, databases, env files,
            and git state.
          </p>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="border-t border-hairline">
        <div className="mx-auto max-w-page px-6 py-24 sm:py-32">
          <div className="mb-12 text-[10px] tracking-wider2 text-muted">
            02 — HOW IT WORKS
          </div>
          <div className="grid grid-cols-1 gap-12 sm:grid-cols-2 md:gap-10 lg:grid-cols-4">
            <Step
              num="01"
              label="ORCHESTRATE"
              body="Describe a high-level task. Claude decomposes it into parallel subtasks, one per agent."
            />
            <Step
              num="02"
              label="ISOLATE"
              body="Each agent gets a git worktree on its own branch, a Docker Compose project with remapped ports, and a rewritten .env."
            />
            <Step
              num="03"
              label="OBSERVE"
              body="A terminal dashboard streams live logs from every agent in parallel."
            />
            <Step
              num="04"
              label="MERGE"
              body="Branches merge sequentially. Conflicts route to a dedicated Claude Code session with the original task context."
            />
          </div>
        </div>
      </section>

      {/* COMMANDS */}
      <section className="border-t border-hairline">
        <div className="mx-auto max-w-page px-6 py-24 sm:py-32">
          <div className="mb-10 text-[10px] tracking-wider2 text-muted">
            03 — COMMANDS
          </div>
          <dl className="border-y border-hairline text-[13px]">
            {COMMANDS.map(([cmd, desc]) => (
              <div
                key={cmd}
                className="flex flex-col gap-1 py-3 sm:flex-row sm:items-baseline sm:gap-8 sm:py-4"
              >
                <dt className="break-words font-medium text-fg sm:w-72 sm:shrink-0">
                  {cmd}
                </dt>
                <dd className="text-fg/55">{desc}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-hairline">
        <div className="mx-auto flex max-w-page items-center justify-between px-6 py-8 text-[11px] tracking-wider2 text-muted">
          <span>TREEHOUSE · MIT · 2026</span>
          <a
            href="https://github.com/ka1kqi/treehouse"
            target="_blank"
            rel="noreferrer noopener"
            className="focus-ring transition-colors hover:text-accent"
          >
            SOURCE ↗
          </a>
        </div>
      </footer>
    </main>
  );
}

function Step({
  num,
  label,
  body,
}: {
  num: string;
  label: string;
  body: string;
}) {
  return (
    <div>
      <div className="mb-4 flex items-baseline gap-3">
        <span className="text-[11px] tracking-wider2 text-muted">{num}</span>
        <span className="text-[11px] tracking-wider2 text-accent">{label}</span>
      </div>
      <p className="text-pretty text-[14px] leading-relaxed text-fg/80">
        {body}
      </p>
    </div>
  );
}
