# CLAUDE.md — mcp/ (THE PRODUCT)

**This folder is the main deliverable.** Cairn as an MCP server, so Claude Code, Codex or
Cursor becomes the brain and gets a browser that remembers websites.

Phase 2. Read `PLAN.md` for what to build, `PROGRESS.md` for where we are. Root rules in
`../CLAUDE.md` apply. Depends on `package/` (Phase 1) only.

## Why this shape (do not drift back)

The host AI does the thinking. Cairn supplies the browser and the memory. That means: no API
key for us or the user, one-command install, and a judge can try it inside their own Claude
Code. Warm replay is deterministic — zero model calls.

## Stack (versions verified 2026-08-31)

Python 3.11+ · official `mcp` SDK 2.1.1 **or** `fastmcp` 3.4.7 (decide at build time after
opening both docs — RESEARCH rule) · the cairn package installed editable.

## The one architecture rule

Thin wrapper. Imports `package/` ONLY — never backend/ or frontend/. No browser logic, no
Sibyl calls, no model calls here. Each tool is a few lines calling into `cairn`. If a tool
needs real logic, that logic belongs in the package.

## Tools to expose

**Cold path (the host AI drives these to learn a new site):**

| tool | does |
|---|---|
| `cairn_act(intent, action, ref?, value?, to?)` | ONE tool for all 29 actions, chosen by the `action` argument |
| `cairn_read(kind, ref?, attribute?)` | `kind="page"` lists the controls; the other 12 kinds read one element |
| `cairn_save(task)` | distil this session's trace into a playbook, store it |

**One tool per verb, never one tool per action (locked 2026-09-01).** Tool choice is the
most fragile part of this system — on the first live test a host AI ignored Cairn and used
`curl`. Twenty-nine tool names to choose between makes that worse, not better. Both tool
descriptions are GENERATED from `actions.ACTIONS` and `reads.READS`, so an action can never
exist without being discoverable.

**Warm path (one call, no thinking):**

| tool | does |
|---|---|
| `cairn_run(task, site)` | replay the playbook deterministically; repairs a broken step by asking the host AI only for that step |
| `cairn_sites()` | learned sites + playbook health |
| `cairn_show(domain)` | the playbook, human-readable |
| `cairn_forget(domain)` | wipe a site's memory — the gate test, from inside any MCP client |

Tool descriptions ARE the UX — the host AI decides what to call from them alone. One dedicated
revision pass on the wording is mandatory before this phase is done.

## Clean code rules

- One file if it fits (`server.py`), two at most. Type hints, ruff clean.
- Long operations must report progress, never hang the client silently.
- Errors return readable messages, never stack traces.
- Never print to stdout — it corrupts stdio MCP transport. Log to stderr only.

## Definition of done

Works from a CLEAN Claude Code session in a DIFFERENT folder + install instructions tested by
following them literally + PROGRESS.md updated.
