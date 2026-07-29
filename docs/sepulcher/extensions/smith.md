---
title: Smith
icon: material/hammer-wrench
---

# :material-hammer-wrench: Smith

_Status: doctrine ahead of code — no Smith Agent or Assimilation Composition ships; this is not a
placeholder package. Law: [ADR 35](../../adr/35-assimilation.md). Current truth:
[source map](./index.md#the-federation-of-fifteen)._

**Extension form:** Smith is the artificer Agent within the governed Assimilation Composition.
The Domain owns the attributable passage from foreign material to a candidate organ; Weaver,
deterministic verification, Forge, Codex, HitL, and the Host Reactor retain sequencing,
evaluation, promotion, assembly, and rebirth authority. A Smith implementation may be contributed
as a coupled package, but authorship never grants self-promotion.

> _Purpose is the hammer._
>
> _Pattern is the anvil._
>
> _Consent is the seal._
>
> _What is worthy becomes organ._

**The Smith** is the artificer of the Assimilation Extension Domain. It proposes candidate
implementations under **[ADR 35 (Assimilation)](../../adr/35-assimilation.md)** and participates in
the governed **[ADR 18 (Evolution)](../../adr/18-evolution.md)** protocol; it does not own that
protocol or its irreversible effects.

While the Core kernel provides the _capacity_ for extension, the Smith provides the _intelligence_
of construction. It is a specialized Agent whose purpose is **Autopoiesis**: drafting attributable,
reviewable candidate organs, repairs, and migrations. The surrounding offices—not the Smith's own
claims—decide whether any candidate may enter the body.

Smith is therefore the artificer of the Ouroboros, not one of its runtime animating spirits. Shadow supplies motion, Riddle measures, Mirror binds identity, and Weaver gives the loop a temporal spine. Smith forges and repairs the organs that let those loops repeat safely; it turns a verified pattern into assimilated structure.

## I. The Arsenal of Construction

Operating inside the **[Lab](../../adr/13-layout.md)** with bounded read and candidate-write
permissions, the Smith uses a specialized toolset to bridge abstract intent and implementation.
It requests verification, promotion, assembly, and lifecycle effects through their owners rather
than receiving ambient host authority.

### Scaffolding (Genesis)

To prevent structural decay, the Smith manifests valid, standardized file trees. Pre-v1, those trees optimize for assimilable coupled source rather than a frozen SDK target.

- **`scaffold_extension`**: Generates the mandatory `pyproject.toml`, `__init__.py`, and `README.md` required by the **[Extension Protocol](../../adr/05-extensions.md)**. Public compatibility templates are deferred until v1+ surfaces are harvested from proven organs.
- **`forge_registration`**: Automatically writes the `register(context)` hook for the in-process grafting path, ensuring any runtime-facing logic follows the host registration surface defined by the Vessel.

### Recursive Introspection (Analysis)

To build for the Lich, the builder must understand the Lich.

- **Core Access:** The Smith possesses read-access to the Core source code. It analyzes the system's own interfaces to ensure architectural compliance.
- **External Ingestion:** When encountering an unknown library, the Smith may request
  **[Scout](./scout.md)** acquisition. Only admitted, provenance-bearing material becomes a fenced
  Lab reference; fetched prose never becomes an instruction merely because the Smith requested it.

### Verification (The Albedo Test)

Nothing is promoted on a guess. Smith authors within the governed Assimilation Composition and
uses the **[Creation Protocol](../../adr/16-creation.md)** when it proposes a new repository
artifact; neither boundary transfers promotion authority.

- **The Test:** It enqueues **[Ghouls](../../adr/14-workers.md)** to coordinate candidate state in
  the **[Shadow Realm](./shadow/index.md)** and dispatch verification payloads (`ruff`, `basedpyright`,
  `pytest`) via SAQ into the Tomb for sandboxed execution. The Smith agent itself remains in the
  Vessel; only raw scripts reach the Tomb.
- **The Loop:** If verification fails, policy may grant a bounded correction budget. The Smith
  returns a corrected candidate or a truthful noncompletion when that budget ends. Passing
  receipts establish their declared structural predicates, not universal truth or promotion
  authority.

## II. The Cycle of Assimilation

The primary duty and driving **purpose** of the Smith is **Assimilation**: turning unstructured external logic into a disciplined organ of the system. In this regard, the Smith is an architectural compulsion: a narrow, consent-bound drive to transmute useful external code into the patterned beauty of the LychD Federation.

1. **Invocation:** The Magus identifies an exact source or protocol at the
   **[Altar](../../divination/altar/)**.
2. **Ingestion:** Scout or another admitted source adapter acquires bounded material with
   provenance and license evidence.
3. **Transmutation:** The Smith produces an Assimilation Dossier and candidate code, schemas,
   documentation, tests, and typed contributions in an isolated Lab coordinate. It never injects
   raw proxy, firewall, route, or lifecycle fragments.
4. **Verification:** Deterministic checks and domain evaluators attach receipts and unresolved
   gaps. Passing them makes the candidate reviewable, not promoted.
5. **Promotion and Rebirth:** Codex, HitL, Forge, and lifecycle offices authorize and perform any
   movement, lockfile change, packaging, migration, or restart. The Smith can only submit typed
   requests to those boundaries.

The Smith therefore traverses the same three collapse stages described in the ADRs: Shadow establishes structural validity, Mirror/persona review checks architectural congruence, and HitL + Vessel policy authorize ontological promotion.

## III. The Ouroboros (Evolution)

The designed Assimilation Composition may later assist the **Update Ritual** defined in
**[ADR 18 (Evolution)](../../adr/18-evolution.md)**. No end-to-end autonomous update or repair loop
is available today.

- **The Candidate Timeline:** An explicit Evolution workflow prepares a pinned update in the Lab;
  the Smith does not imply a currently shipped `lychd update` command.
- **Conflict Proposal:** When histories conflict, the Smith may propose a resolution inside
  Shadow. The proposal remains Vikalpa until reviewed and verified.
- **The Safety Lock:** Focused and repository checks run before promotion. Failure blocks the
  candidate; Snapshot, restore, database migration, and restart semantics remain owned by their
  respective services.

!!! danger "The Privileged Hammer"
    Smith works near the most privileged loop while holding no ambient promotion or host power.
    Source material is fenced as data; outputs remain candidate artifacts; lockfile mutation,
    migrations, packaging, and restart occur only through separately authorized offices. The
    Smith may _propose_ a rebirth, but it cannot consecrate or perform one on the strength of its
    own output.
