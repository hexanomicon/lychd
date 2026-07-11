---
title: 12. Configuration
icon: material/cog-box
---

# :material-cog-box: 12. Configuration: The Codex

!!! abstract "Context and Problem Statement"
    Configuration fragmentation creates structural blindness. When intent is scattered across hardcoded paths, environment variables, and implicit runtime state, the system loses determinism. In a Sepulcher that bridges Host and Container, this fragmentation produces port collisions, permission mismatches, and non-reproducible infrastructure states.


---

## Requirements

- **Single Source of Truth:** All user intent must reside within a bounded configuration domain.
- **Type Authority:** Configuration must be validated through explicit schemas before any infrastructure is generated.
- **One Settings Root:** Only the root `Settings` object may inherit `BaseSettings`; nested sections are ordinary `BaseModel` values reached through that root.
- **Pure Loading:** Loading configuration is read-only. It must not create files, generate credentials, mutate the environment, or silently repair invalid input.
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

Python consumers enter through `lychd.config.settings`. It exports `Settings`,
`get_settings`, and every named configuration section type (for example,
`ServerSettings` and `SwitchingSettings`). The section model modules are an
internal file layout; callers do not import from them. A loaded root is still
navigated as `settings.server`, `settings.orchestration`, and
`settings.extensions`.

Its only top-level sections are:

- `[server]`: the one LychD process and services it operates — HTTP, database,
  Vite, logging, and in-process queue workers.
- `[orchestration]`: semantic run routing and runtime-switching policy.
- `[extensions]`: explicitly selected optional extensions.

The bootstrap server accepts only loopback bind addresses (`127.0.0.1` or
`::1`). It has a fixed trusted local Sigil, not caller authentication. External
traffic must enter through the authenticated Ward/Proxy path defined by IAM.

Extension instance intent belongs to its Rune. In particular, model mounts,
runtime images, portals, and coven membership do not belong in global settings.

The caged foundation selects the Host Reactor explicitly in the generated default tree:

```toml
[orchestration.switching]
actuator = "host-reactor"
reactor_ack_timeout_s = 120.0 # claim deadline; claimed work remains fenced to terminal status
```

`host-reactor` writes typed transition intents to the configured `host_reactor_dir` and is the
normal caged default. Selecting `systemd` is an explicit uncaged/development choice that gives the
process direct access to the user Systemd bus. Durable graph checkpoints are owned by Postgres;
there is no Stasis filesystem path or Vessel checkpoint mount.

The Reactor control path must be absolute and is lexically normalized. It must name an `inbox`
directory; its sibling `journal` is derived rather than configured independently. `lychd init`
provisions both with the owner-only privilege service, so a valid non-default layout is operational
rather than merely parseable. Percent signs, backslashes, and non-printable characters are rejected
because these paths enter generated systemd units.

`reactor_ack_timeout_s` must be positive and bounds only the unclaimed inbox phase. On expiry the
Vessel retracts an unclaimed file before failing. If the host already moved it to `.processing`,
the queue/admission barrier remains closed until a read-only `.completed`, `.declined`, or
`.rejected` terminal receipt appears; this prevents delayed effects from escaping the logical drain
window. A `.declined` receipt proves a failed precondition before effects and reopens the initial
forward barrier without mutation containment.

Schema authority for global settings resides in `src/lychd/config/settings/`:
`root.py` composes the root; one file each owns server, orchestration, and
extensions. Each owner validates rules local to its own settings branch.
`src/lychd/config/components.py` consumes the validated settings object into framework component configuration.

It carries no multi-instance infrastructure definitions.

If secret references are declared in Codex:

- The file must be owned by the Magus.
- File permissions must be `0600`.
- `lychd doctor` fails its preflight if ownership or group/other permissions are unsafe.

The Global config defines global truth.

---

## 2. The Schema Layer (`src/lychd/config/settings/`)

The Schema Layer provides type authority and deterministic loading.

It is implemented using Pydantic and defines:

- Required fields
- Strict typing
- Secret-reference enforcement for credentials (`*_secret` fields)
- One `BaseSettings` root (`Settings`) with ordinary strict `BaseModel` sections beneath it;
  unknown fields and obsolete section names abort loading
- Deterministic source precedence (`Settings.settings_customise_sources()`):

```txt

Explicit construction → Environment Overrides → `lychd.toml` → Pydantic File Secrets → Model Defaults

```

Environment variables enter through the root using `env_nested_delimiter="__"`. The grammar is
`SECTION__FIELD`, extended one segment per nested model; for example,
`SERVER__PORT=9011` overrides `server.port`, while
`SERVER__DATABASE__PORT=5433` overrides `server.database.port` and
`ORCHESTRATION__SWITCHING__DRAIN_TIMEOUT_S=30` overrides the nested switching value.
Nested models do not load their own environment, dotenv, TOML, or secret sources. This preserves
one precedence order and prevents a section from becoming a second, invisible settings root.

The v1 physical queue-worker topology is fixed to `runs` and `rites`. Their
capacity is explicit in `[server.jobs]` as `interactive_concurrency` and
`background_concurrency`; adding a physical worker queue is a composition change, not
an unchecked TOML spelling. Partial `[orchestration.routing]` entries merge onto
the required semantic routes and may name only those fixed physical queues.

Constructing `Settings` is a read-only parse and validation operation. It never inscribes the
Codex and never invents missing secrets. Explicit secret properties resolve from a named
environment value or a mounted file only when needed and fail closed when neither source is
present. Secret creation belongs to an explicit operator/bind ritual, not configuration loading.

If `.env` files are enabled:

- They must reside within the Codex boundary.
- They must be `0600`.
- Permission violations must fail the deployment preflight.

The Schema Layer validates global state before any infrastructure intent is processed.

Exact source precedence and root composition are implemented in
`src/lychd/config/settings/root.py`:

??? example "Live snippet: `src/lychd/config/settings/root.py`"
    ```python
    --8<-- "src/lychd/config/settings/root.py:17:77"
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

The path names the Animator; capabilities are synthesized per-model within it and take their identity from the capability key, not the filesystem. One rune file is one animator instance (a container or portal), while a multi-model runtime behind it yields several capabilities keyed by model within that single instance.

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

### Capability Declaration Doctrine

A passthrough Soulstone declares a single Animator instance, yet the runtime behind it may serve several models with different capabilities. To describe them, a Soulstone rune may carry `[[models]]` blocks, each binding a `ModelCapabilityHints` declaration to a model id:

- `families`: the routable service kinds the model answers (chat, embedding, and so on).
- `surface` and `modalities_in` / `modalities_out`: what the model admits and emits.
- `supports_tools`, `supports_streaming`: runtime behaviour flags.
- `max_context`: the model's context window.

These `[[models]]` blocks are capability declarations *within* one instance, not instance encoding; the arrays-of-tables prohibition of the Instance Doctrine still forbids encoding multiple instances in one file. Absent any declaration, the runtime profile's `text`/`text` default stands. Where a declaration is present, its hints merge over the runtime profile defaults during catalog synthesis, so declared capability is authoritative and the profile supplies only what the declaration omits.

Capability hints are declarations *about the model*, not re-typed framework flags; execution-passthrough purity is preserved. The **[Dispatcher (22)](22-dispatcher.md)** consumes these hints as the declared half of the Declare-then-Verify Doctrine, where live probes may only downgrade a declared capability, never invent one.

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
`[extensions].builtins` and `[extensions].crypt`. Built-ins are resolved through
a trusted, static catalog, then the selected builtin's own `register(context)`
shim performs the contribution. Crypt organs follow the selected-shim rule from
the local extension root. The selected shim writes into explicit registration
stores on `ExtensionContext`.

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
builtins = []
crypt = ["my-private-organ"]
```

All extensions are inactive until explicitly named. `lychd init` writes
commented catalog examples beside the empty list; it does not activate every
installed runtime. This avoids the bootstrap paradox where
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

The global `lychd.toml` is emitted from the validated default `Settings` tree by a real TOML
writer. `None` values are omitted; mappings, arrays, paths, and nested models retain their TOML
types and table ancestry. A newly inscribed file must parse back through a fresh `Settings`
process to the same JSON-mode model dump. This **init round-trip gate** is part of the foundation:
`lychd init` is invalid if the next `lychd` invocation cannot load what it wrote.

Generated sample TOMLs are marked with `# lychd: sample-rune`. The loader skips
marked files before schema validation, so first-run placeholders do not break
`lychd bind`. Removing that marker promotes the TOML into real configuration.

Generic local runtimes are passive by default. Non-model runtimes must declare capability hints explicitly, and local OpenAI-compatible APIs must select an explicit OpenAI-compatible runtime alias or a dedicated adapter. Endpoint presence is not configuration authority for model binding.

`lychd bind` is the separate manifestation ritual. After the complete settings/rune tree validates,
it transmutes the active configuration into Quadlets and plain user-systemd units. In the caged
default this includes the host-only `lychd-reactor.path` and `lychd-reactor.service` units; the
Vessel receives the configured Reactor inbox read-write and its host-owned sibling journal
read-only so the actuation barrier can observe terminal receipts.

The Scribe's authority is exact, not suffix-based. The Quadlet binding site contains one owner-only
`.lychd-owned.json` manifest whose separate sets name the exact LychD-owned Quadlet and
plain-systemd files across both shared binding sites. A bind may replace or remove only those
recorded names. The authority file must be a regular non-symlink owned by the invoking UID with
exact mode `0600`. Duplicate or unsafe manifest entries, invalid authority metadata, malformed
ownership data, and a generated name already occupied by an unowned file fail closed. Staging,
same-filesystem replacement, and prepared backups allow a failure at either binding site to restore
the previous files and ownership manifest.

Anchor creation and sample inscription (`ConfigWriter`) are implemented in `src/lychd/config/runes/writer.py:16`:

??? example "Live snippet: `src/lychd/config/runes/writer.py:16`"
    ```python
    --8<-- "src/lychd/config/runes/writer.py:16:132"
    ```

### The Rite of Inscription (Writable Codex)

`ConfigWriter` writes sample runes at `lychd init`; sanctioned runtime writes to live Codex intent follow a stricter path. When the system itself originates a rune write — the Smith promoting a forged Organ into an activation list (**[Assimilation (35)](35-assimilation.md)**), or the Altar's Bindings instrument editing a rune (**[Altar (15)](15-frontend.md)**) — the write proceeds as a **Rite of Inscription**:

1. The change is composed into a staging file rather than mutating the live TOML in place.
2. The full `ConfigLoader` validates the staged tree exactly as it would at bind time, so an invalid write can never become live intent.
3. Only after validation succeeds is the staging file promoted by atomic rename.
4. A reload signal reloads the Codex from the newly inscribed tree.

Every such write is a hard-gated class. It already qualifies under "core logic promotion" in the Autonomy Policy (§10) and therefore requires live HitL or explicit Codex preauthorization; adaptive confidence never satisfies it. The Smith and the Bindings instrument are the only sanctioned writers of live Codex intent; no other component may mutate a rune after load. This is consistent with the frozen Instance Doctrine: the Rite does not mutate a rune in place, it re-inscribes and reloads.

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
   - Generate the Pod/Container Quadlets and any selected host user units.
   - Commit only the exact Scribe-owned files and update `.lychd-owned.json` transactionally.

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

The loader never generates fallback secret material. A secret value is resolved only from an
explicit local/test environment value, an explicit `*_FILE` override, or the declared mounted Podman secret
path. Generated Quadlets use only the file form; they never place a secret value in the environment.
Because an explicitly injected value wins, production operators must not inject one. Missing,
unreadable, or empty secret files are errors. `lychd bind` may perform an explicit
provisioning/reconciliation ritual for core Podman secrets, but that mutation is not part of
`Settings()` or `get_settings()`.

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
Phylactery-backed policy records, when enabled for adaptive tuning, must remain equal or stricter than the Codex baseline; the comparison is enforced by the Policy Ward (§10).

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

### The Policy Ward

The tighten-only law shared by the Privatization Policy (§9) and the Autonomy Policy (§10) is not self-enforcing. Comparing a baseline against an adaptive layer requires a named seat that performs the comparison; that seat is the **Policy Ward**.

The ConfigLoader establishes the baseline at bind time. The Policy Ward, a Vessel service, is the seat of the comparison: it must reject any adaptive policy write to the Phylactery whose effective permissiveness exceeds the Codex baseline. The comparison is performed at write time, fail-closed. An adaptive record may only equal or tighten the baseline; a write that would loosen it never lands. This tighten-only enforcement is the deliberate mirror of the Declare-then-Verify probing law in the **[Dispatcher (22)](22-dispatcher.md)**, where live probes may only downgrade a declared capability.

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
| Mounts | Codex RO; Lab RW; Core/Extensions RO; Reactor inbox RW plus sibling journal RO only when selected. No blanket Crypt mount. | No Codex mount; task-safe facts travel in the job envelope and only disposable task paths may be RW. |
| Network | Resolves provider and broker routes per policy. | No direct secret-bearing provider routes. |
| Queue Ownership | Owns queue workflow configuration. | No queue configuration ownership. |
| Context Privatization | Defines thresholds and anonymization policy for portal egress. | Cannot lower thresholds or bypass sanitization gates. |
| Autonomy Policy | Defines preauthorization, HitL, and denial classes. | Cannot authorize promotion or broaden its action class. |
| Authority Boundaries | Defines and signs runtime envelopes. | Consumes envelope; cannot redefine authority. |

Soulstones are a separate data-plane configuration consumer, not a third source of Codex truth.
Their generated units receive only explicitly configured model/runtime volumes and unit-scoped
secrets—never the Codex, Crypt, trigger, Reactor inbox, Reactor journal, or user-systemd
binding sites. Global defaults, rune volumes, and adapter-contributed volumes all pass through the
same gate: host and container endpoints must be absolute, host symlink aliases are resolved, and a
path equal to, containing, or contained by a protected control root fails binding. A safe existing
host alias is rendered as its resolved canonical target, pinning the path that passed validation
rather than leaving a retargetable symlink in the unit. The same systemd-unsafe character gate
applies to both mount endpoints.

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
