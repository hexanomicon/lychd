---
title: 12. Configuration
icon: material/cog-box
---

# :material-cog-box: 12. Configuration: The Codex

!!! abstract "Context and Problem Statement"
    Configuration fragmentation creates structural blindness. When intent is scattered across hardcoded paths, environment variables, and implicit runtime state, the system loses determinism. In a Sepulcher that bridges Host and Container, this fragmentation produces port collisions, permission mismatches, and non-reproducible infrastructure states.

    A sovereign system requires a single source of truth, strict validation before manifestation, and a deterministic mapping between filesystem topology and runtime behavior.

---

## Requirements

- **Single Source of Truth:** All user intent must reside within a bounded configuration domain.
- **Type Authority:** Configuration must be validated through explicit schemas before any infrastructure is generated.
- **Deterministic Discovery:** Filesystem hierarchy must uniquely determine rune ownership and instance identity.
- **Fail-Fast Validation:** Port conflicts, branch-owned TOML files, duplicate instance identity, and schema violations must abort loading before Quadlets are written.
- **Secret Discipline:** Sensitive values must be protected from accidental exposure and validated for permission correctness.
- **Privatization Policy:** Context egress thresholds and anonymization requirements must be configurable as first-class policy.
- **Autonomy Policy:** Preauthorization for low-risk autonomous actions must be explicit, fail-closed Codex policy rather than an implicit model confidence shortcut.
- **Extensibility Contract:** Extensions must integrate into the configuration system without custom parsers or ad-hoc loading logic.
- **Infrastructure Integrity:** Configuration must be fully validated before container units are manifested.

---

## Considered Options

!!! failure "Option 1: Monolithic Configuration"
    Placing all configuration — global settings and multi-instance infrastructure — into a single `lychd.toml`.

    - **Pros:** Easy to locate and edit.
    - **Cons:** **Structural Degeneration.** Instance identity becomes implicit. Ordering matters. Silent overwrites become possible. Extension grafting becomes fragile.

!!! failure "Option 2: Environment-Driven Configuration"
    Relying primarily on environment variables or distributed `.env` files.

    - **Pros:** Familiar pattern.
    - **Cons:** **Opaque State.** Environment variables are invisible to version control and cannot express multi-instance topology. Structural validation cannot occur before process startup.

!!! success "Option 3: Layered Codex Architecture"
    Separating configuration into a typed Schema Layer and anchored Rune Schemas.

    - **Pros:**
        - **Deterministic Topology:** Directory structure defines rune ownership.
        - **Type Enforcement:** All configuration validated through Pydantic models.
        - **Coupled Extension Compatibility:** Built-in and private extensions inheriting `RuneConfig` participate in the same loading model.
        - **Fail-Fast Infrastructure:** Quadlets are generated only after full validation succeeds.
        - **Clear Secret Model:** Explicit at-rest protection and runtime boundary definition.

---

## Decision Outcome

A layered configuration system is adopted, structured around the **Codex**.
This ADR defines the Codex contract (global settings, rune schemas, ownership, discovery, validation, and loading order). [Layout (ADR 13)](./13-layout.md) defines the filesystem geography and mount topology where that contract resides.

The Codex resides at:

```txt

~/.config/lychd/

```

XDG path resolution and Host/Container symmetry for this domain are specified in [Layout (ADR 13)](./13-layout.md).

It contains two distinct domains:

1. **The Application Settings**
2. **Rune Schemas**

---

## 1. The Application Settings (`lychd.toml`)

Contains **global configuration only**.

Examples include:

- Application-level settings
- Core service configuration
- Coven alliances
- Global defaults

Schema authority for global settings resides in `src/lychd/config/settings.py`.
`src/lychd/config/components.py` consumes the validated settings object into framework component configuration.

It carries no multi-instance infrastructure definitions.

If secret references are declared in Codex:

- The file must be owned by the Magus.
- File permissions must be `0600`.
- Startup validation emits a structured warning if permissions are broader.

The Global config defines global truth.

---

## 2. The Schema Layer (`src/lychd/config/settings.py`)

The Schema Layer provides type authority and deterministic loading.

It is implemented using Pydantic and defines:

- Required fields
- Strict typing
- Secret-reference enforcement for credentials (`*_secret` fields)
- Deterministic source precedence (`Settings.settings_customise_sources()`):

```txt

Init kwargs → Explicit Environment Overrides → Pydantic dotenv source, when enabled → `lychd.toml` → File Secrets → Model Defaults

```

Environment variables enter through explicit override channels in the schema loader.
If `.env` files are enabled:

- They must reside within the Codex boundary.
- They must be `0600`.
- Permission violations produce warnings.

The Schema Layer validates global state before any infrastructure intent is processed.

Exact source precedence and reserved-port validation are implemented in `src/lychd/config/settings.py:281`:

??? example "Live snippet: `src/lychd/config/settings.py:281`"
    ```python
    --8<-- "src/lychd/config/settings.py:281:371"
    ```

---

## 3. Runes (Instance Scrolls)

Infrastructure intent is declared through runes.

A **rune** is one validated TOML configuration document under the Codex `runes/` tree. It describes extension-owned intent; it is not the final runtime object and not the generated Systemd/Quadlet artifact.

Each rune class:

- Inherits from `RuneConfig`
- Declares `path_fragment` as the single safe relative path segment it contributes; no rune type may place TOML files directly under the rune root
- Uses safe fragment segments: lowercase ASCII letters, digits, `_`, and `-`, length 1-50, starting and ending alphanumeric
- Uses Python subclassing as rune path ancestry; `relative_path` is computed from the single direct rune parent plus the local fragment
- Keeps source provenance as runtime-only instance metadata; `source_file` is derived from the filesystem path and is not a TOML field
- Relies on runic identity and domain validation for required named instances; no base-loader singleton override exists

Rune instances are stored as TOML files under their Anchor directory.

### Rune And Runic Boundary

`RuneConfig.__init_subclass__()` enforces rune anchor rules at class declaration time. Concrete `RuneConfig` subclasses declare `path_fragment` as a `Path`; the computed `relative_path` is relative to the Codex rune root:

??? example "Live snippet: `src/lychd/config/runes/base.py:10`"
    ```python
    --8<-- "src/lychd/config/runes/base.py:28:86"
    ```

`RuneConfig` is the base contract for typed TOML runes:

??? example "Live snippet: `src/lychd/config/runes/base.py:10`"
    ```python
    --8<-- "src/lychd/config/runes/base.py:16:142"
    ```

`Runic` is only a runtime provenance protocol. Any object with `.rune` can be treated as a servant of the Codex backed by a validated rune; that does not make the object a rune class.

??? example "Live snippet: `src/lychd/config/runes/protocols.py:1`"
    ```python
    --8<-- "src/lychd/config/runes/protocols.py:1:27"
    ```

Example structure:

```txt

~/.config/lychd/
lychd.toml
runes/
  animator/
    soulstones/
      vision.toml
      ocr.toml
    portals/
      openai/
        main.toml

```

---

### The Anchor Doctrine

Each `RuneConfig` rune class owns exactly one anchor territory.

- Folder location determines rune type.
- The declared `path_fragment` is local to the rune class.
- Each `path_fragment` must be one path segment matching `^[a-z0-9](?:[a-z0-9_-]{0,48}[a-z0-9])?$`.
- Python subclassing is rune path ancestry and must form a single direct parent chain.
- Mixins/composition should carry shared fields that do not need a new anchor or path fragment.
- `relative_path` is the resolved Codex-root-relative anchor assembled from ancestry.
- Anchors may not overlap.
- No internal `type=` switching is permitted.
- The filesystem hierarchy is authoritative.

Rune ownership is structural, not dynamic.

Loader enforcement for anchor scanning, branch-file rejection, top-level TOML payload, and duplicate identity rejection lives in `src/lychd/config/runes/loader.py:19`:

??? example "Live snippet: `src/lychd/config/runes/loader.py:19`"
    ```python
    --8<-- "src/lychd/config/runes/loader.py:19:180"
    ```

---

### Fragment Path Tradeoff

`path_fragment` keeps declarations short while preserving a concrete computed
anchor:

```python
class SoulstoneConfig(AnimatorConfig):
    path_fragment: ClassVar[Path] = Path("soulstones")

class LlamaCppSoulstoneConfig(SoulstoneConfig):
    path_fragment: ClassVar[Path] = Path("llamacpp")
```

This means Python inheritance is filesystem ancestry for `RuneConfig`
subclasses. That coupling is intentional inside the core and coupled extension
path because it keeps declarations readable and makes branch/leaf topology
mechanical.

The tradeoff is that schema-only reuse should not be modeled as a `RuneConfig`
parent. Use a mixin or composed Pydantic model when shared fields should not move
the class in the Codex tree:

```python
class GenerationDefaultsMixin(BaseModel):
    temperature: float = 0.7

class LlamaCppSoulstoneConfig(SoulstoneConfig, GenerationDefaultsMixin):
    path_fragment: ClassVar[Path] = Path("llamacpp")
```

Provisional structural extension schemas that do not inherit `RuneConfig` cannot
derive a parent chain; they expose a full `relative_path` at the current
schema-intake boundary instead.

`AnimatorConfig` and `SoulstoneConfig` are abstract branch configs. They are
configuration base classes, but they are not direct TOML owners. Concrete
Soulstone TOML instances must live under a leaf schema such as
`LlamaCppSoulstoneConfig`, `VllmSoulstoneConfig`, or `SglangSoulstoneConfig`.

---

### The Instance Doctrine

Within an Anchor:

- One TOML file equals one instance.
- Instance payload resides at TOML top level (arrays-of-tables are forbidden for instance encoding).
- Instance identity is derived from relative path.
- Duplicate identity across files is forbidden.
- Validated rune instances are frozen. Resolvers and runtime handles may derive
  effective state from a rune, but they must not mutate Codex intent after load.

If a rune class has children, it is a branch namespace and may not own TOML files in its own anchor.

Leaf rune classes may define multiple instances.

Branch anchors are not profile buckets. If a branch needs reusable profiles,
those profiles must be modeled as their own leaf rune family and referenced by
name from the capability-bearing rune. This keeps parent/default runes single
and makes many-profile configuration explicit.

Violations abort configuration loading.

### Semantic Profile Doctrine

Filesystem ancestry must not masquerade as semantic defaults.

Shared defaults that apply only to a capability family, such as LLM generation settings, should become named rune/profile instances and be referenced by capability-bearing runes. For example, a generative Soulstone or Portal may reference a generation profile and add local overrides, while a web crawler or tool-only animator never receives irrelevant generation fields just because it lives under `animator/`.

Resolvers compute effective runtime config from:

- named profile runes
- runtime/family defaults
- local rune overlays
- request-time overrides

This keeps directory layout useful for discovery while semantic policy remains explicit and capability-scoped.

---

### llama.cpp Preset Doctrine (`--models-preset`)

`llama.cpp` soulstones may reference a router preset `.ini` via a typed rune field (e.g., `preset_path`), allowing the Magus to preserve optimized upstream launch profiles while remaining inside Codex governance.

- **Two-Tier Intent:**
    - **Rune Intent:** Identity, coven policy, and runtime launch shape.
    - **Preset Intent:** Router/runtime defaults and per-model launch arguments consumed by `llama-server`.
- **Validation Rule:** Preset references must resolve to an existing readable file path before binding; unresolved preset paths are configuration errors.
- **Boundary Rule:** Preset files tune model runtime behavior, but may not redefine host-level governance authority enforced by LychD (port arbitration, coven exclusivity, and orchestration ownership).
- **Precedence Awareness:** Preset semantics follow upstream llama.cpp precedence (CLI > model section > global section). Codex manifests should document any CLI overrides that intentionally shadow preset values.

This doctrine preserves "Magus heritage" tuning while preventing configuration fragmentation.

---

### The Leaf Principle

Only leaf rune classes (those without subclasses) may define multiple instances.

Non-leaf rune classes are branch namespaces only. They share fields and code defaults with descendants but do not own TOML instances. In animation, this means `AnimatorConfig` and `SoulstoneConfig` are ABC-style branch configs, not files such as `runes/animator/animator.toml` or `runes/animator/soulstones/foo.toml`.

There is no explicit singleton override in `RuneConfig`. If a domain requires one specific named instance, or requires that one named instance be active, that is domain validation rather than base rune authority.

This prevents ambiguous discovery, implicit polymorphic loading, and ad hoc singleton exceptions in the base loader.

## 4. The Configurable Contract (Extension Integration)

Configuration extensibility is governed by the structural registry of the Core.

However, per the **[Extension Compatibility Tiers (ADR 05)](05-extensions.md#7-extension-compatibility-tiers)**, not every external organ has the same stability promise.

To resolve this **Codex Paradox**, rune classes follow tiered integration paths:

- **Built-in Extensions:** May inherit directly from `RuneConfig`.
- **Private Coupled Extensions:** May inherit directly from `RuneConfig` if the operator accepts refactor coupling.
- **Future Independent Extensions:** Must wait for a versioned public schema API before LychD promises Core-refactor compatibility.

### Registration Doctrine (The Machinery's Translation)

Rune schema registration belongs to runtime/extension composition, not to the
rune loader. Enabled extensions import or register their active `RuneConfig`
classes before Codex inscription or runtime loading. The rune layer then receives
an explicit `list[type[RuneConfig]]` and performs only filesystem anchoring,
sample writing, TOML parsing, and Pydantic validation.

In the current implementation, `ExtensionManager` assembles this list from
`[extensions].builtins` and `[extensions].crypt`. Built-ins are resolved inside
the trusted `lychd.extensions.builtin` namespace by convention, then the selected
builtin's own `register(context)` shim performs the contribution. Crypt organs
follow the same selected-shim rule from the local extension root. The selected
shim writes into explicit registration stores on `ExtensionContext`.

Store ownership stays with the layer that owns the concept:

- `context.runes` is a Codex/rune store and receives `RuneConfig` schemas.
- `context.soulstones` is an Animator store and receives `SoulstoneDefinition`
  objects; each definition registers its rune schema and exposes its runtime
  adapter.

The same activation decision therefore feeds Codex inscription/loading,
Animator loading, Quadlet planning, and Dispatcher-facing capability binding
without the rune loader scanning packages or knowing extension internals.

Extension activation itself is configured outside extension-owned runes. Core
`lychd.toml` names active built-in and Crypt organs with lists:

```toml
[extensions]
builtins = ["observability/phoenix", "animator"]
crypt = ["my-private-organ"]
```

All omitted extension ids are inactive. This avoids the bootstrap paradox where
Codex would need an extension's rune schema in order to decide whether that same
extension should be imported. Once selected, the extension may register rune
schemas; those runes configure selected extension instances, not extension
existence.

No extension may implement custom configuration loaders, and no dynamic `type=` dispatch is permitted.

Registration automatically binds the rune class to:

```txt
~/.config/lychd/runes/<relative_path>/
```

If an extension is installed:

1. Its selected `register(context)` shim contributes `RuneConfig` subclasses into `context.runes`.
2. Their Anchors become valid Codex territories.
3. One TOML file equals one instance and payload lives at TOML top level.
4. Instances located in those directories are validated and loaded.
5. Validated instances become configuration intent.
6. A separate factory, adapter, or domain store contribution must hydrate that intent into runtime state when the rune is meant to do work.

Extension import alone does not register **rune ownership** under the shared loader. The explicit registration store does. A rune schema alone does not by itself register a runtime service.

The Codex loader remains singular and authoritative.

---

### Structural Guarantees

This model ensures:

- Extensions cannot fragment configuration loading.
- Configuration remains globally validated.
- Infrastructure manifestation remains downstream of schema authority.
- Removal of an extension invalidates only its anchor territory.

Configuration extensibility is therefore achieved without sacrificing determinism.

## 5. Port Arbitration

Port ownership is validated before Quadlet generation.

The validator aggregates:

- Reserved core ports
- Ports declared by Rune Schemas

If any collision is detected:

- Configuration loading fails immediately.
- No Quadlets are written.

Infrastructure is never generated from invalid state.

---

## 6. Runtime Realization (`lychd init`)

At runtime, initialization follows a deterministic inscription path:

1. `lychd init` calls `CodexService.inscribe()`.
2. Runtime/extension composition supplies the active `RuneConfig` schema classes.
3. `ConfigWriter.initialize_anchors()` materializes all anchor directories.
4. `ConfigWriter.inscribe_samples()` writes one sample TOML per schema only when no instance file exists yet.

This keeps extension activation outside the rune filesystem layer.
Animation follows the same path: `AnimatorLoader` consumes the same `RuneConfig` runes under `runes/animator/`.

Generated sample TOMLs are marked with `# lychd: sample-rune`. The loader skips
marked files before schema validation, so first-run placeholders do not break
`lychd bind`. Removing that marker promotes the TOML into real configuration.

Generic local runtimes are passive by default. Non-model runtimes must declare capability hints explicitly, and local OpenAI-compatible APIs must select an explicit OpenAI-compatible runtime alias or a dedicated adapter. Endpoint presence is not configuration authority for model binding.

Anchor creation and sample inscription (`ConfigWriter`) are implemented in `src/lychd/config/runes/writer.py:16`:

??? example "Live snippet: `src/lychd/config/runes/writer.py:16`"
    ```python
    --8<-- "src/lychd/config/runes/writer.py:16:132"
    ```

---

## 7. Assembly Pipeline

The configuration lifecycle proceeds in strict order:

1. Load Global config.
2. Validate Schema Layer.
3. Discover Anchored Rune Schemas.
4. Validate each instance.
5. Enforce:
   - Duplicate identity rejection
   - Domain identity and policy constraints
   - Port arbitration
6. Only after full validation:
   - Generate Quadlets.

Infrastructure is a manifestation of validated intent.

---

## 8. Secret Covenant

Secrets are declared by reference:

- Codex stores secret names (`*_secret`) only.
- Soulstones may map runtime env vars to secret names via `secret_env_files`.
- Values live in rootless Podman secret storage.
- Generated Quadlets bind them through `Secret=` directives.

Secrets:

- Are not stored inline in `lychd.toml` or rune TOMLs
- Are mounted only into units that require them
- Are accessible to the process boundary that consumes them

Example lifecycle:

```bash
printf '%s' "$OPENAI_API_KEY" | podman secret create --replace portal_openai_main -
podman secret ls
```

Filesystem permissions protect secrets from other host users.
They do not protect secrets from code executing within the same Quadlet unit.

If isolation from agent-level execution is required, the secret must reside in a separate service boundary.

---

## 9. Context Privatization Policy

Privatization policy is configured in the Codex and enforced by runtime dispatch:

- `portal_threshold`: minimum weight requiring anonymization before portal egress.
- `forbidden_threshold`: minimum weight forbidding raw portal egress.
- `require_anonymization_workflow`: fail-closed if no sanitization path exists.

Canonical source is Codex (`lychd.toml`).
Phylactery-backed policy records, when enabled for adaptive tuning, must remain equal or stricter than the Codex baseline.

Conceptual shape:

```toml
[security.privatization]
portal_threshold = 0.40
forbidden_threshold = 0.70
require_anonymization_workflow = true
```

---

## 10. Autonomy and Approval Policy

Autonomy policy is configured in the Codex and enforced by trusted Vessel-side gates. The baseline is fail-closed: if no policy explicitly authorizes an autonomous action, the action requires **[HitL (ADR 25)](25-hitl.md)** or is denied.

This policy exists to distinguish three different meanings that older prose sometimes compressed into "approved":

- **Live Magus approval:** an explicit decision at the Altar.
- **Preauthorized Vessel policy:** a bounded rule written by the Magus and validated by the system before execution.
- **Denied authority:** a class of action the system may simulate, test, or report on, but may not promote.

ZTE chores are not a bypass around consent. They are a named preauthorization class for minor, reversible, well-tested work where the Codex policy, deterministic verification, identity constraints, and safety boundaries all agree.

High-stakes classes remain hard gated by live HitL regardless of confidence score:

- core logic promotion
- schema migration
- destructive data deletion
- secret or credential changes
- network or egress broadening
- host lifecycle authority
- spending above configured toll limits
- cross-identity memory sharing

Conceptual shape:

```toml
[autonomy]
default_action = "require_hitl"

[autonomy.zte]
enabled = true
max_risk = "minor"
requires_clean_checks = true
requires_snapshot = false
min_streak = 8
min_confidence = 0.95
allowed_scopes = ["docs", "tests", "non_runtime_metadata"]
forbidden_scopes = ["core_runtime", "migrations", "secrets", "host_lifecycle"]
```

Canonical source is Codex (`lychd.toml`). Phylactery-backed performance records, confidence streaks, and adaptive policy observations may tighten the effective policy or satisfy a Codex-defined predicate, but they must not loosen the Codex baseline.

---

## 11. Dual-Plane Trust Delta

Configuration is now split by trust boundary:

- Vessel config is the only source of truth for secrets, persistence, and policy.
- The Tomb config is a generated runtime envelope with only task-safe fields.
- The Tomb config is derived data, never an alternate source of truth.
- The Tomb schema forbids provider secret fields and infrastructure authority fields.
- Provider/API keys are never serialized into Tomb payloads.
- Narrow queue-only SAQ/Postgres execution credentials, when needed, are worker-unit credentials rather than Tomb configuration authority.
- The Tomb cannot override queue, network, autonomy, approval, or authority policy.

### Authority Matrix

| Dimension | Vessel (Trusted Control Plane) | The Tomb (Untrusted Execution Plane) |
| :--- | :--- | :--- |
| Secrets | Loaded via Podman secret references and mounted into trusted units. | Provider and authority secret fields are forbidden by schema; narrow queue-only SAQ/Postgres execution credentials live at worker-unit policy. |
| Mounts | Codex-backed config and durable state mounts. | Sanitized task-scoped config artifact or read-only projection only. |
| Network | Resolves provider and broker routes per policy. | No direct secret-bearing provider routes. |
| Queue Ownership | Owns queue workflow configuration. | No queue configuration ownership. |
| Context Privatization | Defines thresholds and anonymization policy for portal egress. | Cannot lower thresholds or bypass sanitization gates. |
| Autonomy Policy | Defines preauthorization, HitL, and denial classes. | Cannot authorize promotion or broaden its action class. |
| Authority Boundaries | Defines and signs runtime envelopes. | Consumes envelope; cannot redefine authority. |

## Consequences

!!! success "Positive"
    - **Deterministic Topology:** Filesystem structure defines rune ownership and instance identity.
    - **Fail-Fast Guarantees:** Invalid configuration aborts before infrastructure generation.
    - **Extension Uniformity:** Coupled extensions inheriting `RuneConfig` integrate without custom configuration loaders.
    - **Clear Trust Boundaries:** Secret visibility is explicit and aligned with process boundaries.

!!! failure "Negative"
    - **Strict Structural Discipline:** Incorrect directory placement or duplicate identity causes immediate failure.
    - **Shared Process Trust Domain:** Secrets available to a Quadlet unit are accessible to code within that unit.
    - **Operational Responsibility:** File permissions must be maintained to preserve at-rest protection.
