# File Editing

## Trigger

Load this playbook after the domain scope when the task authorizes changes under tracked source or
tests. It defines the **Edit Agent** procedure. It grants no permission beyond the user's task and
does not replace the owning ADR, source, tests, or contribution rules.

## Edit contract

Before the first patch, establish:

| Field | Required answer |
| --- | --- |
| Target | Exact files or bounded subtree |
| Intent | Observable behavior or defect being changed |
| Base | Current revision and relevant dirty-worktree overlap |
| Owners | ADR/topic, source boundary, tests, generated contract, or dependency behavior |
| Effects | Allowed writes, commands, migrations, generation, and external actions |
| Non-goals | Adjacent cleanup and authority explicitly left untouched |
| Gates | Closest failing test, focused checks, and necessary wider boundary checks |

Refuse or escalate when the edit would require guessing authority, migration, rollback, secret
handling, compatibility, or destructive scope.

## Just-in-time file rules

After discovery and immediately before editing, load exactly one matching card when available:

- [Python](python.md) for `.py`;
- [JavaScript and TypeScript](javascript-typescript.md) for `.js`, `.jsx`, `.ts`, or `.tsx`.

Svelte files continue through the tracked frontend and Svelte scopes; those owners already carry
the framework-specific workflow. When a task crosses file types, load the next card at the
boundary rather than preloading all cards. For TOML, JSON, YAML, SQL, shell, CSS, fixtures, and
other types without a card, continue with this generic procedure and the selected domain scope.
Absence of a specialized card is not a refusal condition.

## Procedure

1. **Probe the behavior.** Read the target, direct callers, closest tests, public/export boundary,
   and any generated or persisted counterpart.
2. **State the invariant.** Describe what must remain true before proposing a patch.
3. **Patch narrowly.** Preserve unrelated dirty changes and avoid opportunistic rewrites.
4. **Test from the inside out.** Start with the closest oracle, then widen only across affected
   boundaries.
5. **Inspect the diff.** Check accidental API, schema, dependency, generated-file, documentation,
   and delivery drift.
6. **Return a receipt.** Name changed behavior, files, checks, unrun live-host evidence, and any
   remaining risk.

## Recovery

- A failed focused test is evidence; do not weaken the test, add a skip, or widen a timeout unless
  the owning contract requires that change.
- If formatting or generation changes unrelated files, isolate the intended mechanical output and
  leave user changes intact.
- If dependency behavior is unclear, inspect the installed version and its source before browsing
  or guessing.
- If the first patch exposes a different owner, stop editing, load that owner, and restate the
  contract.

An Edit Agent may propose a candidate. Acceptance, promotion, deployment, and destructive cleanup
remain with their ordinary owners.
