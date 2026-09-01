"use client";

import { useState } from "react";

const INSTALL = "claude mcp add cairn -- uvx cairn-mcp";

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
