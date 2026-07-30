---
title: 12. Configuration
icon: material/cog-box
---

# :material-cog-box: 12. Configuration

!!! abstract "Context and decision"
    The Codex holds declared operator intent. A single typed Settings root and anchored Rune
    instances are read, validated, attributed, and assembled before they can project infrastructure.

## Settings: one immutable generation

`lychd.toml` is the global Settings document under the Codex. Its only top-level sections are
`server`, `orchestration`, and `extensions`. `Settings` is the sole `BaseSettings` model; nested
strict `BaseModel` sections reject unknown and obsolete fields. The public Python entry is
`lychd.config.settings`, not its internal section modules.

Source precedence is fixed:

```txt
explicit construction → environment → lychd.toml → Pydantic file secrets → model defaults
```

Environment names use the root `SECTION__FIELD` grammar. There is no dotenv source and nested
sections do not load separate environment, TOML, or secret sources. Loading is read-only: it does
not create Codex files, repair input, generate credentials, or mutate the environment.
`SettingsSnapshot` captures a validated serialized generation; each preview/apply phase
materializes and revalidates its own copy rather than retaining mutable nested models.

`[extensions]` selects permitted built-in and Crypt packages; it neither selects an application nor
creates a runtime. A future application selector requires its own accepted Weaver schema and may
resolve only registered revisions. Settings owns the fixed `runs` and `rites` physical queues and
their concurrency; routing can name only those queues. Global port claims and Rune port claims are
arbitrated before any unit is written.

## Runes: location, provenance, semantics

A Rune is one validated top-level TOML instance in the Codex `runes/` tree, not a runtime object
or generated unit. Each concrete `RuneConfig` supplies one safe `path_fragment`; direct Python
subclassing forms one anchor ancestry, and `relative_path` is computed from it. A fragment is one
segment matching `^[a-z0-9](?:[a-z0-9_-]{0,48}[a-z0-9])?$`. Anchors cannot overlap. Branch
classes are namespaces and cannot own TOML files; only leaf schemas may have one or more
instances. A file's path supplies its identity and `source_file` provenance. Duplicate identity,
files in branch anchors, arrays-of-tables instance encoding, unsafe fragments, and schema
violations abort discovery.

An **Anchor** is an owned directory territory. A **Fragment** is its safe local path segment. An
**Instance** is one leaf TOML document. Provenance follows an instance at runtime but is not a TOML
field. Validated instances are frozen: resolvers may derive effective state but may not alter
Codex intent.

Filesystem ancestry names type, not semantic defaults. Named leaf profile instances supply
family-specific defaults; a capability-bearing Rune references profiles and applies local overlays.
Resolvers combine profile, runtime/family defaults, local overlay, then request-time override.
Presets such as a `llama.cpp` router `.ini` are typed, readable references: they tune their runtime
but cannot change port arbitration, coven exclusivity, or host ownership. Upstream precedence is
`CLI arguments > model-specific preset section > global [*] section`; a generated CLI override
that deliberately shadows a preset value must remain visible to the operator.

Capability declarations such as `[[models]]` describe models behind one Rune instance, including
families, modalities, tool/streaming support, and context size. They are not a way to encode
multiple instances. Capability synthesis begins with text input and output. Field precedence is
Rune hint, then live probe or adapter-discovered runtime fact, then runtime profile default. An
explicit modality hint replaces discovered and default modalities; when omitted, probed modalities
may enrich the runtime base. [Dispatcher (22)](22-dispatcher.md) may verify a declared capability
only by downgrading it.

## Extension activation and application selection

Selected extension registration shims add `RuneConfig` types to `context.runes`; the loader is
given that explicit schema list and never scans packages. A `Configurable` extension registers its
schema through this contract, then separately registers any runtime definition or adapter in its
own domain store. Importing a package does not register it; registering a schema does not create a
service. Extensions cannot introduce custom loaders, source precedence, parsers, or `type=`
dispatch. [Extensions (05)](05-extensions.md) owns compatibility tiers.

## Realization and the writable Codex

`init` and `init --dry-run` derive the same `LifecyclePlan`. The real command rejects UID 0,
inscribes missing anchors and inactive leaf samples, and must round-trip a generated Settings TOML
through fresh validation. Marked samples are ignored until their marker is removed. `bind` first
uses one immutable Settings/extension/Rune generation to compile declarations, then revalidates
the foundation, secret presence, generations, and receipts under the lifecycle lock immediately
before mutation. A content-identical reconciliation is a no-op; an indeterminate mutation keeps
recovery evidence. [Layout (13)](13-layout.md) owns path creation, locks, receipts, and filesystem
attestation; [Security (09)](09-security.md) owns trusted executables and permissions.

The assembly pipeline is: load and validate Settings; assemble selected schemas; discover and
validate Rune instances; enforce identity, domain policy, and ports; then project only exact
Scribe-owned units. Downstream registries consume that generation and must not reopen the Rune
filesystem.

A sanctioned live Codex writer is designed separately from current sample writing. It must stage a
typed request, validate the complete staged tree as bind would, atomically rename only after that
validation, and use an explicit reload signal. It has no ambient authority from Smith or Altar.
Core promotion needs live HitL; a narrower preauthorization must be expressly lawful. No hot
reload is delivered. [State of Work](../state-of-the-work.md#smith-forge-promotion) records this
path as Designed.

## Secrets, privacy, autonomy, and projections

Codex stores only secret references (including `*_secret`), never values. Resolution occurs at the
consumer from an explicit value, `*_FILE`, or declared mounted Podman secret; missing, empty, or
unsafe sources fail closed. Bind preflight requires the Codex secret file to be Magus-owned with
group and other permissions closed. Generated units use file form and scope mounts to the unit that
needs them. Filesystem permissions do not isolate code within that unit.

Codex also sets the privacy/egress baseline (thresholds, anonymization requirement, destination
and purpose eligibility, non-declassifiable categories, transformer/verifier profile, receipt
lifetime, revision) and autonomy baseline. The Policy Ward rejects adaptive Phylactery state that
is more permissive than Codex. Absent explicit authorization, effects require HitL or are denied;
confidence does not authorize core promotion, migrations, destructive deletion, secret changes,
egress broadening, host authority, excessive spending, or cross-identity memory sharing.

Vessel configuration is the source of truth. A future Tomb envelope is derived, secret-free, and
cannot alter queues, network, mounts, privacy, autonomy, approval, or authority. Tomb receives no
Codex mount. [Security (09)](09-security.md) owns credentials and isolation; the Tomb delivery
boundary remains [Designed](../state-of-the-work.md#tomb-untrusted-execution).
