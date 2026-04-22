# Agent Drift Ledger

This ledger tracks recurring mistakes made by LLM agents in this repository. It is intended to be used as a pre-coding checklist to avoid common pitfalls.

## Rule Matrix

| Rule | Tool | Caught | Avoid | Do |
| :--- | :--- | :--- | :--- | :--- |
| Structlog exception usage | `review` | 1 | Logging exceptions loosely or using ambiguous `error=` payloads | Use `logger.exception(...)` for active exceptions |
| Nested `if` | `ruff` | 1 | Two nested `if` blocks when one condition or guard clause works | Prefer combined conditions or guard returns |
| Markdown bullet style | `markdown` | 1 | Star bullets (`*`) or malformed nesting | Use flat `-` bullets and `- **Label**` style |
| Legacy generic boilerplate | `basedpyright` | 2 | `TypeVar(...)` on Python 3.12+ | Use PEP 695 syntax (e.g., `class Runic[T](...)`) |
| Invalid `type` alias | `basedpyright` | 1 | `type T = TypeVar("T", ...)` | Use `T = TypeVar("T", ...)` or PEP 695 |
| Early repo-wide checks | `review` | 1 | Running full lint/type-check immediately after small edits | Run targeted `make lint RUFF_TARGETS="..."` first |
| Transitional shims | `review` | 1 | Adding temporary aliases or compat layers during refactors | Perform direct rewrites in target modules |
| Ruff import sort (I001) | `ruff` | 1 | Changing imports without re-checking sorted order | Run targeted lint after import rewrites |
| Unused imports (F401) | `ruff` | 1 | Keeping stale imports after structural refactors | Trim imports before type-check/tests |

## Detailed Notes

### Ruff / Formatting
- Add repeated Ruff failures here (import style, `__all__` ordering, simplification, logging patterns).
- Prefer pattern guidance over one-off error transcripts.

### BasedPyright / Typing
- Add repeated strict-typing failures here (nullability, protocol contracts, missing return paths).
- Include the correct pattern that prevents recurrence.
