"use client";

import { useState } from "react";

const CMD = "pip install treehouse";

export default function InstallButton() {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(CMD);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <button
      onClick={copy}
      className="focus-ring border border-hairline px-4 py-2 text-[13px] tracking-wider2 text-fg transition-colors hover:border-accent hover:text-accent"
      aria-label="Copy install command"
    >
      {copied ? (
        <span className="text-accent">copied</span>
      ) : (
        <span>
          <span className="text-muted">$</span> pip install treehouse
        </span>
      )}
    </button>
  );
}
