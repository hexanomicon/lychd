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
- **Deterministic Discovery:** Filesystem hierarchy must uniquely determine schema ownership and instance identity.
- **Fail-Fast Validation:** Port conflicts, duplicate singleton declarations, and schema violations must abort loading before Quadlets are written.
- **Secret Discipline:** Sensitive values must be protected from accidental exposure and validated for permission correctness.
- **Privatization Policy:** Context egress thresholds and anonymization requirements must be configurable as first-class policy.
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
        - **Deterministic Topology:** Directory structure defines schema ownership.
        - **Type Enforcement:** All configuration validated through Pydantic models.
        - **Extension Compatibility:** Any extension inheriting `RuneConfig` participates in the same loading model.
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

Init kwargs → Explicit Environment Overrides → Codex `.env` → `lychd.toml` → File Secrets → Model Defaults

```

Environment variables enter through explicit override channels in the schema loader.  
If `.env` files are used:

- They must reside within the Codex boundary.
- They must be `0600`.
- Permission violations produce warnings.

The Schema Layer validates global state before any infrastructure intent is processed.

Exact source precedence and reserved-port validation are implemented in `src/lychd/config/settings.py:321`:

??? example "Live snippet: `src/lychd/config/settings.py:321`"
    ```python
    --8<-- "src/lychd/config/settings.py:321:372"
    ```

---

## 3. Rune Schemas (Instance Scrolls)

Infrastructure intent is declared through Rune Schemas.

Each schema:

- Inherits from `RuneConfig`
- Declares `relative_path` rooted at `~/.config/lychd/runes/` (or `None` for runes root)
- Uses `singleton: bool | None` where `None` enables auto topology inference

Rune instances are stored as TOML files under their Anchor directory.

Example structure:

```txt

~/.config/lychd/
lychd.toml
runes/
  animator/
    animator.toml
    soulstones/
      vision.toml
      ocr.toml
    portals/
      openai.toml

```

---

### The Anchor Doctrine

Each `RuneConfig` schema owns exactly one anchor territory.

- Folder location determines schema type.
- Anchors may not overlap.
- No internal `type=` switching is permitted.
- The filesystem hierarchy is authoritative.

Schema ownership is structural, not dynamic.

Loader enforcement for anchor scanning, singleton exclusivity, top-level TOML payload, and duplicate identity rejection lives in `src/lychd/config/runes/loader.py:19`:

??? example "Live snippet: `src/lychd/config/runes/loader.py:19`"
    ```python
    --8<-- "src/lychd/config/runes/loader.py:19:102"
    ```

---

### The Instance Doctrine

Within an Anchor:

- One TOML file equals one instance.
- Instance payload resides at TOML top level (arrays-of-tables are forbidden for instance encoding).
- Instance identity is derived from relative path.
- Duplicate identity across files is forbidden.

If a schema resolves as `singleton`, only one file may exist.

Violations abort configuration loading.

---

### The Leaf Principle

Only leaf schemas (those without subclasses) may define multiple instances by default.

Non-leaf schemas are singleton by default.

Explicit `singleton=True/False` overrides auto behavior.

This prevents ambiguous discovery and implicit polymorphic loading.

## 4. The Configurable Contract (Extension Integration)

Configuration extensibility is governed by a single structural contract: `RuneConfig`.

Any extension that wishes to declare configuration must:

- Inherit from `RuneConfig`
- Declare `relative_path` (or `None` for top-level singleton)
- Optionally declare `singleton` override

Example contract and helper methods are defined directly in `src/lychd/config/runes/base.py` (see `RuneConfig` snippet above).

### Registration Doctrine

Configuration schemas are registered structurally, not procedurally.

- The subclass itself is the registration signal.
- Runtime import plus subclass discovery determines ownership.
- No extension may implement custom configuration loaders.
- No dynamic `type=` dispatch is permitted.

Inheritance automatically binds the schema to:

```txt
~/.config/lychd/runes/<relative_path>/
```

If an extension is installed:

1. Its `RuneConfig` subclasses are discovered.
2. Their Anchors become valid Codex territories.
3. One TOML file equals one instance and payload lives at TOML top level.
4. Instances located in those directories are validated and loaded.
5. Validated instances become infrastructure intent.

Extension import + inheritance registers **schema ownership** under the shared loader.

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
2. `RuneSchemaDiscovery.discover_classes()` imports built-in extensions and discovers all `RuneConfig` subclasses.
3. `ConfigWriter.initialize_anchors()` materializes all anchor directories.
4. `ConfigWriter.inscribe_samples()` writes one sample TOML per schema only when no instance file exists yet.

This keeps extension configuration registration structural (inheritance/import), not procedural.
Animation follows the same path: `AnimatorLoader` consumes the same `RuneConfig` runes under `runes/animator/`.

Discovery import + subclass traversal (`RuneSchemaDiscovery`) is implemented in `src/lychd/config/runes/discovery.py:10`:

??? example "Live snippet: `src/lychd/config/runes/discovery.py:10`"
    ```python
    --8<-- "src/lychd/config/runes/discovery.py:10:53"
    ```

Anchor creation and sample inscription (`ConfigWriter`) are implemented in `src/lychd/config/runes/writer.py:16`:

??? example "Live snippet: `src/lychd/config/runes/writer.py:16`"
    ```python
    --8<-- "src/lychd/config/runes/writer.py:16:70"
    ```

---

## 7. Assembly Pipeline

The configuration lifecycle proceeds in strict order:

1. Load Global config.
2. Validate Schema Layer.
3. Discover Anchored Rune Schemas.
4. Validate each instance.
5. Enforce:
   - Singleton exclusivity
   - Duplicate identity rejection
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

## 10. Dual-Plane Trust Delta

Configuration is now split by trust boundary:

- Vessel config is the only source of truth for secrets, persistence, and policy.
- Shadow config is a generated runtime envelope with only task-safe fields.
- Resource policy is centralized in Vessel and enforced at dispatch time.

### Boundary Configuration Rules

- Shadow config is derived data, never an alternate source of truth.
- Shadow schema forbids secret fields and infrastructure authority fields.
- Provider/API keys are never serialized into Shadow payloads.
- Shadow cannot override queue, network, or authority policy.

### Policy Table

| Dimension | Vessel (Trusted Control Plane) | Shadow (Untrusted Execution Plane) |
| :--- | :--- | :--- |
| Secrets | Loaded via Podman secret references and mounted into trusted units. | Secret fields are forbidden by schema. |
| Mounts | Codex-backed config and durable state mounts. | Sanitized task-scoped config artifact only. |
| Network | Resolves provider and broker routes per policy. | No direct secret-bearing provider routes. |
| Queue Ownership | Owns queue workflow configuration. | No queue configuration ownership. |
| Context Privatization | Defines thresholds and anonymization policy for portal egress. | Cannot lower thresholds or bypass sanitization gates. |
| Authority Boundaries | Defines and signs runtime envelopes. | Consumes envelope; cannot redefine authority. |

## Consequences

!!! success "Positive"
    - **Deterministic Topology:** Filesystem structure defines schema ownership and instance identity.
    - **Fail-Fast Guarantees:** Invalid configuration aborts before infrastructure generation.
    - **Extension Uniformity:** Any extension inheriting `RuneConfig` integrates without special handling.
    - **Clear Trust Boundaries:** Secret visibility is explicit and aligned with process boundaries.

!!! failure "Negative"
    - **Strict Structural Discipline:** Incorrect directory placement or duplicate identity causes immediate failure.
    - **Shared Process Trust Domain:** Secrets available to a Quadlet unit are accessible to code within that unit.
    - **Operational Responsibility:** File permissions must be maintained to preserve at-rest protection.
