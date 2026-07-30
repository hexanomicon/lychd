# Python Editing

Load this card immediately before changing `.py` files, after the Build scope and any matching
architecture owner.

## Inspect before patching

Read:

- the complete target module and its module docstring;
- class, function, method, and field docstrings on the changed path;
- signatures, type parameters, overloads, protocols, Pydantic models/validators, and public
  exports;
- direct callers and the closest positive, negative, and recovery tests;
- serialization, database, migration, CLI, API, or generated-schema counterparts when present;
- `pyproject.toml`, `uv.lock`, and installed dependency source when versioned behavior matters.

Docstrings reveal intended use and drift; they are not stronger than accepted law, source, or
tests. If behavior changes, update an owning docstring in the same patch. Do not add narration that
merely restates names and types.

## Change discipline

- Preserve the supported Python range and project typing conventions.
- Keep domain calculation separate from filesystem, process, systemd, network, database, and
  other physical effects.
- Preserve lazy boot imports where startup ordering requires them.
- Do not introduce a facade, compatibility alias, or generic abstraction without a real second
  consumer and owner.
- Treat model validation as shape evidence, not factual or authorization evidence.
- Carry cancellation, idempotency, terminal state, and cleanup through any path that already owns
  them.
- Never hand-edit generated code or a migration whose lineage must instead be regenerated.

## Verify

Start with the closest test node or file. Then run the focused lint/type/test gates from
`CONTRIBUTING.md` for the affected boundary. Widen to integration, architecture, database, or full
repository checks only when the change crosses those contracts.

Before handoff, inspect:

- public signature and import drift;
- changed exceptions, defaults, validation, serialization, and log fields;
- stale docstrings, comments, tests, ADR/topic operation, and State claims; and
- dependency or lockfile changes not explicitly intended.

When a public signature or schema changes, run affected caller/consumer tests. Regenerate and
compare any owned OpenAPI, client, schema, migration, or documentation example instead of
accepting source inspection as parity evidence.
