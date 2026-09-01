import type { ReactNode } from "react";
import { Check, Cross } from "./Glyphs";

/** Outer tile is rounded-xl (24px) with 20px of padding, so anything that hugs
 *  its edge drops one step to rounded-sm — Apple's concentric rule. */
function Tile({ children }: { children: ReactNode }) {
  return (
    <div className="surface flex h-[190px] items-center justify-center overflow-hidden rounded-xl bg-white">
      {children}
    </div>
  );
}

export const CONTROL_TILES = [
  {
    lead: "Stays on your machine",
    body: "Everything Cairn learns is written to one file on your own disk. Nothing is uploaded anywhere.",
    art: (
      <Tile>
        <div className="well w-[74%] rounded-md bg-mist px-4 py-3.5">
          <p className="font-mono text-[12px] text-faint">memory</p>
          <p className="mt-1.5 truncate font-mono text-[13px] text-ink">
            ~/.sibyl-memory/memory.db
          </p>
          <span className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-moss/12 px-2.5 py-1 text-[11.5px] font-medium text-moss">
            <Check className="h-3 w-3" />
            on this computer
          </span>
        </div>
      </Tile>
    ),
  },
  {
    lead: "Uses the AI you already have",
    body: "Claude Code, Cursor, Codex. Cairn is a tool they pick up, not another assistant to learn.",
    art: (
      <Tile>
        <div className="w-[74%] space-y-2">
          {["Claude Code", "Cursor", "Codex"].map((app) => (
            <div
              key={app}
              className="well flex items-center justify-between rounded-sm bg-mist px-3.5 py-2.5"
            >
              <span className="text-[13px] text-ink">{app}</span>
              <Check className="h-3.5 w-3.5 text-moss" />
            </div>
          ))}
        </div>
      </Tile>
    ),
  },
  {
    lead: "No key, no account",
    body: "Nothing to sign up for. A repeat run uses no model at all, so it costs you nothing.",
    art: (
      <Tile>
        <div className="well w-[74%] rounded-md bg-mist px-4 py-4">
          <p className="font-mono text-[12px] text-faint">API key</p>
          <div className="mt-2 flex items-center gap-2">
            <span className="grid h-[18px] w-[18px] place-items-center rounded-full bg-black/8 text-faint">
              <Cross className="h-[11px] w-[11px]" />
            </span>
            <span className="font-mono text-[13px] text-faint">not required</span>
          </div>
        </div>
      </Tile>
    ),
  },
  {
    lead: "Forget on command",
    body: "One command and Cairn forgets a site. The trail is archived, and replay has nothing left to follow.",
    art: (
      <Tile>
        <div className="well w-[80%] rounded-md bg-mist px-4 py-4">
          <p className="font-mono text-[12px] leading-relaxed text-ink">
            <span className="text-faint">$ </span>
            cairn forget --site billing.acme.com
          </p>
          <p className="mt-2 font-mono text-[12px] text-moss">
            archived. 7 steps forgotten.
          </p>
        </div>
      </Tile>
    ),
  },
];
