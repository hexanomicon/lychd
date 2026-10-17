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
`server`, `orchestration`, `extensions`, `weaver`, and optional `archive`. `Settings` is the sole `BaseSettings` model; nested
strict `BaseModel` sections reject unknown and obsolete fields. The public Python entry is
`lychd.config.settings`, not its internal section modules.

### Load and retain one generation

Source precedence is fixed:

```txt
explicit construction → environment → lychd.toml → Pydantic file secrets → model defaults
```

Environment names use the root `SECTION__FIELD` grammar. There is no dotenv source and nested
sections do not load separate environment, TOML, or secret sources. Loading is read-only: it does
not create Codex files, repair input, generate credentials, or mutate the environment.
`get_settings()` retains one loaded generation per process. Runtime consumers use its stored
values; they never reopen environment variables or secret files. Reload requires an explicitly
constructed new `Settings` instance or a process restart. `SettingsSnapshot` retains a secret-free
serialized declaration and the already-loaded credentials separately in memory as `SecretStr`.
Each preview/apply phase revalidates its own copy without running settings sources again.

Every accepted field must have one real consumer. Current Settings exposes `server.port`, but the
native listener host is fixed by runtime policy rather than TOML. Obsolete `server.host`,
`server.reload`, `server.keep_alive`, and `server.web.url` inputs are rejected and do not appear in
generated configuration; launcher flags or environment cannot smuggle them back as Codex intent.

### Current selections

`[extensions]` selects permitted built-in and Crypt packages; it neither selects an application nor
creates a runtime. Settings also owns the fixed `runs` and `rites` physical queues and their
concurrency; routing can name only those queues. Global port claims and Rune port claims are
arbitrated before any unit is written.

The bounded Core Bridge selector is the first local slice: optional
`[weaver.bridge]` requires `revision = "2"` and one exact `capability_key`. It activates the
registered `bridge_chat@2`; omission keeps `bridge_chat@1` active. Admission stamps the selected
key into durable Run intent before publication, and Graph state retains it across pauses. A changed
Settings generation affects new admissions only; idempotent retries keep their original selection.
This is capability identity pinning, not an executable/declaration generation fingerprint or the
general portable Resolution Lock. No configurable pool, arbitrary Pattern, AgentSpec, or Context
profile selector ships through this section.

An explicit `revision = "3"` selects the read-only Archive answer profile and additionally
requires an `archive` binding with exact `local-public-notes@1` profile, namespace UUID, trusted
local subject, and policy revision. It is valid only with PostgreSQL and the same-host bootstrap
custody profile. The whole binding is retained at Run admission; changed settings cannot rewrite
an admitted casting. This selector grants no remote identity, namespace access, ingestion, or
embedding capability. Intake and promotion remain separate explicit Archive operations.

### Exact delegated casting selection

Optional `[weaver.delegation]` selects `revision = "2"`, one exact registered `runtime`, and
`profile` (`read`, `candidate`, or `verify`) for new `/delegate` admissions. Omission retains
the effect-free `delegated_rite@1` reference route. The configured revision retains its runtime
binding in Run intent and Graph state; idempotent admission and restart use that retained binding,
not the current Settings generation. Unknown adapter names refuse assembly. Registration and
selection do not establish host readiness, containment, privacy, or permission to launch.

This section accepts no command, executable, environment, provider credential, model alias,
alternate list, or fallback switch. An adapter's trusted host still owns effect-time admission.
Failure, policy refusal, or an uncertain start never redirects this exact casting to a different
runtime. Provider/Gate configuration and compatible-road fallback need their own admitted contracts.

### Exact Creation investigation selection

Optional `[weaver.creation]` selects `revision = "2"` and one exact `capability_key` for
`creation.investigation@2` / `creation.investigate@2`. Omission disables its admission. This
bounded application requires PostgreSQL, current local operator policy and its fixed
[public-source profile](../compositions/creation/index.md#admit-one-question). The captured local
shared vLLM/Qwen Chat declaration must match its generation and policy; no alias, fallback,
remote route or hardware transition is supplied by selection.

Creation retains source bytes, criteria, complete role bindings and reservation under its own
case before releasing held Run delivery. Current settings cannot rewrite an existing request;
an eligible explicit continuation retains the same case/profile and its original deadline.
Settings carries neither source/prompt material nor a credential or authority grant. The
application rechecks current credential-backed object/action policy at use. This typed selection
does not introduce a general SDLC coordinator or portable Resolution Lock.

### Independent public Archive selection

Optional `[archive]` selects `profile` independently of Bridge. Its profile retains the exact
`local-public-notes@1` schema. Existing `weaver.bridge.archive` configuration remains valid;
when both are supplied they must match exactly, and assembly uses one effective binding.
Omission preserves the existing Bridge selection and disables independent derivation.

Optional `archive.derivation` supplies a generation UUID and an exact Core `EmbeddingBinding`
(capability key, profile digest, `model.embed@1`). The configured registry must admit that local
static profile before assembly succeeds. An HTTP caller cannot provide an endpoint, model,
manifest or fallback. Loading settings and assembling services neither registers a generation
in PostgreSQL nor prepares a model. Explicit authorized registration retains the configured
manifest; explicit derivation requests perform bounded synchronous work.

The derivation Dispatcher shares the application's exact registry and lease ledger but has no
Run event sink. A supplied Run UUID is caller attribution only: it neither establishes a Run
relationship nor permits events or writes to that Run. The existing Graph dispatcher is unchanged.

## Runes: location, provenance, semantics

A Rune is one validated top-level TOML instance in the Codex `runes/` tree, not a runtime object
or generated unit. Each concrete `RuneConfig` supplies one safe `path_fragment`; direct Python
subclassing forms one anchor ancestry, and `relative_path` is computed from it. A fragment is one
segment matching `^[a-z0-9](?:[a-z0-9_-]{0,48}[a-z0-9])?$`. Distinct registered schemas cannot
own the same exact anchor; nested anchors remain distinct and express declared class ancestry.
Nested non-Rune Pydantic value objects may contribute shared validated structure without joining
or branching that anchor ancestry. The delivered `QuadletConfig` is embedded under the `quadlet`
field of Soulstone and Phoenix Runes and shares only the minimum OCI image invariant; it supplies
neither a Rune path nor raw unit, lifecycle, mount, network, secret, or command authority.
Generic sample generation renders required embedded values as typed TOML inline tables; maintained
hand-authored examples may use the equivalent named table form such as `[quadlet]`.
Branch classes are namespaces and cannot own TOML files; only leaf schemas may have one or more
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

### General-service declarations and current model blocks

The accepted general-service Rune shape uses first-class `[[capabilities]]` entries. Each entry
references one registered semantic interface and exact immutable profile, declares its permitted
operations and invocation mode, and pins the runtime driver/dialect, conformance evidence, resource
envelope, and containment profile required to make that instance honest. Definitions are typed
Contributions governed by their receiving Core office or Extension Domain and retain the
Registrant's `registrant_id`; an implementation profile separately names its concrete Provider. A
Rune selects those definitions and supplies instance-local endpoint, secret reference, lifecycle,
and explicit overlay values. It cannot redefine their schemas, licenses, or proved limits inline.

Current source delivers only `[[models]]`: models behind one Rune instance with closed families,
input modalities, Chat or Responses surface, tool support, context size, and generation overlays.
Streaming support and output modalities have no configurable v1 fields. Those blocks remain v1
compatibility sugar for exact admitted model-interface projections; non-model services never
invent a `model_id` or generation overlay merely to become loadable. Neither form encodes multiple
Rune instances.

The single `GenerationProfile` owns the common context, output-token, temperature and top-p
overlays. Its optional closed `thinking = "qwen3.8-non-thinking"` policy is model-local: only an
explicit `[[models]]` generation block for local vLLM `Qwen3.8-27B` on the Chat surface may select
it. Runtime defaults, Soulstone-wide defaults, Portals and other model/runtime/surface combinations
refuse a non-null policy before publication. Omission preserves the existing request. This is one
admitted self-hosted chat-template dialect, not arbitrary provider settings or model-name inference.

For the current v1 path, capability synthesis begins with text input. Field precedence
is Rune hint, then live probe or adapter-discovered runtime fact, then runtime profile default. An
explicit modality hint replaces discovered and default modalities; when omitted, probed modalities
may enrich the runtime base. In v2, open facts are profile-specific and a live probe may establish
readiness but never invent an interface, operation, language, format, dialect, or permission.
[Dispatcher (22)](22-dispatcher.md) may verify a declared capability only by downgrading it.

## Extension activation and application selection

Selected extension registration shims add `RuneConfig` types to `context.runes`; the loader is
given that explicit schema list and never scans packages. A `Configurable` extension registers its
schema through this contract, then separately registers any runtime definition or adapter in its
own domain store. Importing a package does not register it; registering a schema does not create a
service. Extensions cannot introduce custom loaders, source precedence, parsers, or `type=`
dispatch. [Extensions (05)](05-extensions.md) owns compatibility tiers.

The complete preauthorization Rune generation is validated before durable reconciliation.
Duplicate slugs fail deterministically, and an incoming Rune cannot replace a row whose durable
owner is not `codex:rune`. Only after those checks may one transaction refresh Rune-owned rows,
retain their usage and operator-enabled state, mark absent Rune-owned policies unavailable, and
publish newly admitted policies.

## Realization and the writable Codex

`init` and `init --dry-run` derive the same `LifecyclePlan`. The real command rejects UID 0,
inscribes missing anchors and inactive leaf samples, and must round-trip a generated Settings TOML
through fresh validation. Marked samples are ignored until their marker is removed. `bind` first
uses one immutable Settings/extension/Rune generation to compile declarations, then revalidates
the foundation, secret presence, generations, and receipts under the lifecycle lock immediately
before mutation. A content-identical reconciliation is a no-op; an indeterminate mutation keeps
recovery evidence. [Layout (13)](13-layout.md) owns path creation, locks, receipts, and filesystem
attestation; [Privilege (10)](10-privilege.md) owns trusted host executables and their permissions.

The assembly pipeline is: load and validate Settings; assemble selected schemas; discover and
validate Rune instances; enforce identity, domain policy, and ports; then project only exact
Scribe-owned units. Downstream registries consume that generation and must not reopen the Rune
filesystem.
Rune read, syntax and schema-validation failures identify the source file; schema failures retain
their field diagnostics and original validation cause.

A sanctioned live Codex writer is designed separately from current sample writing. It must stage a
typed request, validate the complete staged tree as bind would, atomically rename only after that
validation, and use an explicit reload signal. It has no ambient authority from Smith or Altar.
Core promotion needs live HitL; a narrower preauthorization must be expressly lawful. No hot
reload is delivered. [State of Work](../state-of-the-work.md#smith-forge-promotion) records this
path as Designed.

## Secrets, privacy, autonomy, and projections

Codex stores only secret references (including `*_secret`), never values. Settings sources resolve
the database password and application signing key once during construction into excluded,
non-repr `SecretStr` fields. Explicit construction and root-grammar environment values take
precedence over the existing `LYCHD_DB_PASSWORD` / `LYCHD_APP_SECRET_KEY` environment aliases,
then their `*_FILE` paths, then `/run/secrets/<declared-name>`. TOML credential values are rejected.
An absent default mount leaves the credential unset so host `init` and caged `bind` can run before
provisioning; database/web assembly and uncaged preflight reject unset credentials without I/O.
Uncaged preflight checks the bootstrap database password, runtime database password, local HTTP
access password, and application signing key separately against that captured generation.
Explicit file overrides must be readable and nonempty at Settings construction. Nested settings
models perform validation only; explicitly supplied section instances are complete overrides.
Bind preflight requires the Codex secret file to be Magus-owned with
group and other permissions closed. Generated units use file form and scope mounts to the unit that
needs them. Filesystem permissions do not isolate code within that unit.

### Policy and derived projections

In the accepted design, Codex also sets the privacy/egress baseline (thresholds, anonymization requirement, destination
and purpose eligibility, non-declassifiable categories, transformer/verifier profile, receipt
lifetime, revision) and autonomy baseline. The designed Policy Ward rejects adaptive Phylactery state that
is more permissive than Codex. Absent explicit authorization, effects require HitL or are denied;
confidence does not authorize core promotion, migrations, destructive deletion, secret changes,
egress broadening, host authority, excessive spending, or cross-identity memory sharing.

Vessel configuration is the source of truth. A future Tomb envelope is derived, secret-free, and
cannot alter queues, network, mounts, privacy, autonomy, approval, or authority. Tomb receives no
Codex mount. [Security (09)](09-security.md) owns credentials and isolation; the Tomb delivery
boundary remains [Designed](../state-of-the-work.md#tomb-untrusted-execution).

## Future selectors

### Application and Gateway profiles

Any further application selector requires its own accepted Spellweaver schema and
may resolve only one registered exact profile revision, such as one of the mutually exclusive
[Reach deployment profiles](../compositions/reach/deployments/index.md). In Reach, for each
Discord application and Habitat partition, that immutable selection binds one authority epoch,
one Discord edge epoch, one
active Phylactery, one Gateway/delivery credential owner, and the exact per-host role set. Unknown
mixtures and boolean authority switches such as `trusted`, `use_vps`, `local_db`, or `tether`
fail before Bind. The selected profile contributes no raw units: one immutable generation resolves
its exact Composition/Pattern revisions and registered service roles into the
[`ApplicationDeploymentManifest@1`](08-containers.md#versioned-application-deployments), then
revalidates global ports, routes, secrets, mounts, migrations, dependencies, and resource policy
before Bind.

Changing profile or authority location is a typed Evolution effect, not Settings reload. It must
quiesce admission, settle or preserve external-effect identities, fence the old epochs, revoke old
routes and credential owners, transactionally restore an admitted partition when authority moves,
and activate the new generation last. An old or simultaneous generation fails closed.

Gateway placement follows the same exact-profile law. [Home and Remote](../sepulcher/gateway.md)
are reference placements of one separate Gateway Host role, not applications, Extension
Domains, or free configuration literals. A selected deployment profile either omits that role or
binds its exact per-host manifest, Veil routes, optional Tether generation, backend identity,
service Principals, edge secrets, firewall and management boundaries, and recovery contract.
Loose fields such as `gateway=true`, `rpi`, `vps`, or an arbitrary proxy target cannot assemble a
partial edge.

### Palette configuration

Presentation configuration obeys the same typed-source law when it is admitted. In particular, a
future [Altar palette](15-frontend.md#canonical-appearance-and-bounded-palette-configuration) may
enter only through an explicitly owned validated Settings field or another Covenant-owned typed
source with declared precedence; it is never an unmodelled TOML table, raw CSS file, selector, or
extension side channel. Frontend owns the finite semantic colour roles and accessibility rules,
while Configuration owns loading, validation, attribution, and immutable generation. Current
Settings contains no palette field and changing the accepted root shape requires an implementation
and State update.

### General casting selection

A future [Spellweaver configuration-to-casting selector](28-workflow.md#configuration-to-casting-spine)
follows the same root-shape law. Local TOML may select exact already-registered Scroll, Spell
implementation, `AgentSpec`/Posture, and Context projection revisions plus bounded policy, with the
Agent references resolved only through an exact placement; the portable Scroll remains canonical
JSON. Configuration never names Python imports, BaseNodes, graph edges, callables, prompts, source
bytes, credentials, or live handles, and it cannot turn schema registration into executable
activation.
