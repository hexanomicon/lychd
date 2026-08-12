---
title: 5. Extensions
icon: material/toy-brick-outline
---

# :material-toy-brick-outline: 5. Extensions

!!! abstract "Context and Problem Statement"
    LychD admits native Python where it needs its speed and reach, while keeping authority with
    the domain that receives a contribution. The architecture must also leave a real boundary for
    separate engines, dependencies, images, and lifecycles. The operational journey is owned by
    [the Extensions Sepulcher](../sepulcher/extensions/); this leaf states the constitutional
    boundary.

## Decision Outcome

LychD selects native, protocol-bound contributions for admitted extensions and external service
protocols where isolation or independent deployment is required. An external service for every
extension would buy isolation at latency and deployment cost; sandbox scripting remains a future
containment option, not a second language or runtime promised today.

The Extension Protocol joins local-package admission and external-provider integration without
conflating their trust or lifecycle boundaries. Providers expose functional identities separately
from their concrete implementations. A future Forge lock lifecycle must pin foreign source and
physical inputs; selected import shims alone are not reproducibility evidence.

An **Extension Domain** is one of the fifteen stable user-facing jurisdictions. A **package** is
code; a **Manifestation** is a concrete Core, package, Composition, managed Provider, external, or
dormant profile form. A **Contribution** is a typed addition accepted by its Domain owner, and a
**Provider** is a concrete mechanism. Domain presence proves neither a package nor delivery;
activation is of a concrete package or instance, never an abstract domain. Compositions may use
Domains without becoming one; packages may cross Domains, and one Domain may receive many packages
or Providers.

### Vocabulary Boundary: Domain Is Not Package

The distinction prevents provenance, trust, evolution, and configuration from being collapsed
into import location. Core owns schemas, policies, lifecycle, and host effects. An extension can
contribute only the explicit shapes that a receiving owner accepts.

### 1. The Federation Strategy

The host federates selected in-process Python packages and uses external protocols when needed.
It initializes the extension context once at boot, from configuration, only for selected built-in
and Crypt packages. It discovers neither the environment nor entry points.

Built-ins live under `src/lychd/extensions/builtin/`; Crypt packages are explicitly selected local
`register.py` shims. Installed never means active. The selector is not the future Forge manifest,
which must eventually pin source, dependencies, and physical substrate.

```toml
[extensions]
builtins = []
crypt = ["my-private-organ"]
```

`lychd init` may show commented choices, but the default is inert. A selected package is
imported and calls `register(context)`. Enabling it permits schemas, hydrators, and store
registration; it does not start an instance. Codex receives the resulting schema list, not a
package scan. Built-in dependencies are explicit catalogue edges: selecting a concrete Animator
runtime assembles the shared `animator` base once, under its own provenance, before the runtime.
Crypt activation resolves only that exact `register.py`; it performs no package or entry-point
discovery. The shim is loaded in an injectively named synthetic package so ordinary relative
sibling imports work without making neighboring Crypt packages active.
If import or `register()` fails, the manager removes that synthetic package namespace before
surfacing the error, so a repaired retry cannot inherit half-imported module state.
Activation ids must already be canonical POSIX-relative paths: aliases, traversal, absolute paths,
empty segments, and control characters are refused before import.

### 2. The Registration Surface (The Extension Context)

The context has shaped stores for `runes`, `soulstones`, `portals`, `transmutation`,
`delegated_runtimes`, and `run_operations`; `vessel` is reserved and empty. New contribution kinds
need an explicit owner. Patterns, Compositions, status, routes, tools, workloads, and migrations
are not implied merely because a package registers. A minimal contribution is explicit:

```python
context.runes.add_schema(RuneConfig)
```

The accepted general-service capability surface is Designed and is not present in that context.
It requires separately owned and sealed contribution stores for semantic interface revisions,
immutable profile revisions/digests, Connector dialect-driver revisions, evidence bindings, and
runtime/Portal activation definitions. Registration of one kind grants none of the others:

- an interface defines semantic request/result, operations, typed facets, and failure meaning;
- a profile closes exact model/tool/graph/workflow inputs, licenses, formats, languages, limits,
  resources, and evidence references;
- a dialect driver speaks one exact protocol subset and owns no semantic eligibility;
- an activation definition binds an admitted profile and driver to one Rune schema and lifecycle;
  and
- an evidence binding points to producer-attributed results and an admission decision by the
  target contract owner.

Every identity includes a safe stable id plus immutable revision or digest, provider provenance,
and a single owning contribution. Cross-store references are resolved and validated as one staged
assembly before membership seals. Registering a Rune schema, Python client, URL, or familiar
"OpenAI-compatible" label cannot synthesize any missing contribution.

A versioned application deployment profile is another receiving-owner contract, not raw unit text
or authority inherited from a Composition name. The future sealed `deployment_services` surface
may admit exact service-role contributions from Core or an Extension Domain; Containers owns the
`ApplicationDeploymentManifest@1` physical schema and compiler, Configuration owns selection and
generation assembly, and the application profile owns which registered roles its workload needs.
A contribution pins its owner, implementation revision, IPC contract, lifecycle, secret, network,
mount, resource, and recovery requirements. Registration starts no service and cannot add an
undeclared port, command, mount, network, credential, migration, or dependency during compilation.
This surface is Designed and absent from the current `ExtensionRegistrationContext`.

Future Spell and Scroll contribution preserves that boundary. Spellweaver-owned stores may admit
portable Spell contracts and Scroll declarations; executable implementation and adapter stores
remain separately owned by Extension and effect Domains. Contract publication, implementation
registration, Scroll publication, and activation are distinct acts. None is implied by the current
registration context or by the presence of an equally named package.

Web-acquisition providers preserve the same rule. A package may register an Animator definition
for a search or browser service, but a `SoulstoneDefinition`, `PortalDefinition`, or raw
`ToolConnector` is not a Scout provider registration and grants no Search, Fetch, Crawl, Render,
or Extract authority. The future provider contribution surface must be explicitly Scout-owned,
effect-specific, provenance-preserving, and sealed with the other registration stores. Until that
surface exists, provider-facing toolsets remain incapable of constituting a delivered Scout path.

The manager owns the root context and passes each registrant a provider-bound
`ExtensionRegistrationContext`. User activation IDs remain the Settings and filesystem selectors;
audit provenance uses disjoint trust-domain identities: `core`, `builtin:<activation-id>`, and
`crypt:<activation-id>`. Its shaped store facades capture one fixed provider identity and do
not expose the root provenance mutator; even a retained facade cannot inherit a later registrant's
identity. Stores retain that provenance, reject another provider's replay even when the Python
value is equal, and seal membership after the one assembly pass. `AssembledExtensions` exposes
read projections plus the sealed root context; retained registration methods remain present for
assembly compatibility but reject every post-assembly write. It is not a live registry that
arbitrary runtime code may extend. This seal does not recursively freeze trusted contributed
Python objects; each contribution contract must provide its own immutability or defensive-copy
boundary.

### 3. Contributions as Organs

Runes, Soulstones, Portals, and Transmutation admit active schemas and definitions. A
`SoulstoneDefinition` couples its schema to an Animator-owned runtime adapter and registers that
schema into the shared rune store. Runtime schema discovery imports only the selected package; a
loader is the singular TOML parser and validator, not a ledger. `__subclasses__` may audit an
already-loaded process but cannot establish registration or change whether an admitted schema is a
file-owning leaf. Branch ownership is computed from the exact admitted schema generation. Exact
repeat registration is idempotent
only for the same provider. Rune schema admission also reserves its exact filesystem anchor; a
different schema cannot claim the same `relative_path`. Soulstone registration identity is the
runtime name, Rune schema, and adapter type. The same runtime or schema with another owner fails
closed instead of silently preserving first registration. Portal schemas likewise have one exact
factory owner. Composition passes the definitions, not an ordered list of anonymous callables;
runtime dispatch looks up the Portal's exact Rune schema. A broad factory cannot claim another
package's declaration, and a factory is total for every value its schema admits. Each definition
also owns its optional typed probe strategy. A Portal that requests a live probe without that exact
strategy fails closed; connector shape or a coincidental method name never selects an egress
protocol. The factory protocol is total: schema validation must refuse values its exact owner
cannot construct.

The Rune registry deep-copies admitted schema metadata and every returned snapshot, including
nested mutable values. Membership sealing and snapshot isolation are separate laws: trusted
contributors may still own mutable runtime objects, but callers cannot mutate canonical Rune
metadata through a value returned by the registry.

Every selected `register(context)` shim is a synchronous boot hook and must return `None`.
Awaitables and other return values fail assembly; an async function is never silently admitted as
an unexecuted registration. Crypt failure clears that activation's synthetic import generation.
Live Animator Rune, group, and capability projections add their own defensive-copy boundary before
values cross into orchestration, policy, or adapter code.

Run operations live beneath `lychd run`, carry typed metadata and shared authority traceability,
and do not create a root command or callback. The built-in `delegation` extension has one
no-network reference adapter and fail-closed declarations for provider-backed candidates. A
declaration describes immutable transport, delivery, security, and limitation; it never executes a
matching binary by itself. Registration supplies neither persistence nor infrastructure authority:
those need accepted ordering, recovery, export, deletion, and uninstall contracts.

### 4. Substrate Injections

Operating-system libraries, binaries, images, services, resources, licenses, and wider substrate
requirements enter through the Extension Protocol and Forge manifest, not the boot context. Forge
is where platform validation and operator consent can be made explicit.

### 5. Runtime Schema Discovery

Schema makes TOML loadable; it is not runtime. A domain supplies the runtime definition and
hydrator. LychD-facing state uses `Runic[T]` and its `.rune` provenance; a foreign object is not
`Runic` until an adapter wraps it. Codex validates configuration, an adapter builds state, and the
handle retains the rune while foreign internals remain sovereign. Foreign systems may use rune
machinery, but their stable boundary is translated configuration, not borrowed internals.

### 6. The MPL 2.0 Shield (Private Extensions)

MPL 2.0's file-level terms allow a proprietary separate extension to link with LychD. That is not
a trust decision. A private in-process package can access process memory, so admission remains an
intentional operator and owner choice.

### 7. Extension Compatibility Tiers

#### The Built-in Direct Path

`src/lychd/extensions/builtin/` is core-owned. It may use internals and ABCs because it releases
atomically with the core and is selected by convention.

#### The Private Coupled Path

Crypt packages may live outside the tree while importing internals and `RuneConfig`. This is a
Magus-local, refactor-risking path; Assimilation may repair it, but no compatibility guarantee is
made.

#### The Independent Extension Package Path (v1+)

An independently released extension package is deferred until a versioned public API, conformance tests, and Forge
packaging exist. No SDK is created now and no independent compatibility promise is implied.
Foreign agent frameworks are not first-class in-process runtimes: use an external-service
Animator, A2A Emissary, or `DelegatedAgentNode` adapter, or assimilate their useful patterns.

| Property | Built-in Direct | Private Coupled | Future Independent Package |
| --- | --- | --- | --- |
| Location | `src/lychd/extensions/builtin/` | Magus-owned Crypt space | Forge-managed distribution |
| Coupling | Core internals and subclasses | Internals by choice | Versioned public API only |
| Loader | Selected import + `register(context)` | Selected shim + `register(context)` | Deferred, manifest-gated |
| Release cycle | Atomic with Core | Operator-owned | Independent |
| Stability | Core-maintained | Local repair only | Not promised until productized |

#### Rune And Runtime Boundary

Schemas and wrappers separate `SoulstoneDefinition` from its runtime adapter. Provenance travels
with a rune, not an assumption that foreign objects share core identity.

#### Delegated-Agent Runtime Adapters

An adapter has a schema and declared limits, not a node class. Its exact non-shell builder covers
one audited runtime/version range; it starts, polls or streams, cancels the process tree, and
settles results. Untrusted provider output becomes an `AgentJob` result or event, subject to
usage/rate-limit, reset, health, and provenance observations. It receives a secret-free grant and
[Coffin](./09-security.md#the-coffin-delegated-agent-profile)—not graph access, persistence,
quotas, credentials, promotion, or reanimation—and may emit bounded redacted JSONL, never a hidden
graph or chain-of-thought record. A new provider is an adapter plus configuration contribution, not
a node class or second orchestration kernel. A Provider aggregator is admitted through a
Portal/provider gate and an allowlist.

#### Cross-Language Organs

There is no stable cross-language ABI. Coupled code may be composed and repaired through Forge;
the future public API is the only route to independence. External services provide the present
true separation. LychD performs no blind `.so` scan: binary loading requires the Forge manifest,
platform validation, and explicit operator consent before runtime import.

### Consequences

In-process code shares the daemon and can crash or corrupt it, so only trusted, admitted source
receives that path. Selection and contracts stay explicit. Process isolation, independent
lifecycle, and refactor independence require an external protocol or a future public product;
they are not granted by a package name.
