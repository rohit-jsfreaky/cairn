"use client";

import { useState } from "react";

/**
 * The command a visitor can actually run today.
 *
 * For most of this project's life it read `git clone …`, because nothing was published and a
 * copy button that hands somebody a failing command is worse than a longer honest one. Both
 * packages went up on PyPI on 2026-09-03, so the short version is finally the true one and
 * nobody needs the repository to use Cairn.
 */
const INSTALL = "pip install cairn-browser-mcp";

export function CopyCommand() {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(INSTALL);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  return (
    <button
      type="button"
      onClick={copy}
      className="flex items-center gap-5 rounded-full bg-white/80 py-2.5 pr-2.5 pl-7 ring-1 ring-black/8 backdrop-blur-sm transition-colors hover:bg-white"
    >
      <code className="font-mono text-[14px] text-ink/80">{INSTALL}</code>
      <span className="rounded-full bg-ink px-4 py-2 text-[13px] font-medium text-white">
        {copied ? "copied" : "copy"}
      </span>
    </button>
  );
}
