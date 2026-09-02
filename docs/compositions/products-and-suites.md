---
title: Products and Suites
icon: material/vector-link
---

# :material-vector-link: Products and Suites

A Product is the door an operator recognizes. A Composition is the reusable application owner
behind that door. A Suite is needed only when several such owners must actively coordinate one
result. Keeping those offices separate allows many Products to accumulate without copying domain
truth into every package.

## From promise to one execution

```text
Product-supported use case = a class of operator job
Deployment = one configured Product context for an operator
Pattern within one Composition, or Suite across several = reusable technical realization
Invocation = one admitted Circle for requested work
Run = the durable execution and ledger identity representing that Invocation
```

A Product pins eligible Composition or Suite revisions, owner-qualified profiles, projections,
supported use cases, defaults, and its delivery and support envelope. It owns the promise and
packaging. It owns no member records, judgment, policy, secrets, consent, Sigils, credentials, or
effect authority, and it is not another scheduler or executor.

## Compositions relate without nesting

Do not encode a broad `depends_on: composition` edge. Name the exact relation instead.

| Relation | Meaning | Suite? |
| --- | --- | --- |
| Product co-packaging | one Product offers several independently usable capabilities | no |
| settled typed reference | one owner reads an exact already-settled record, ArtifactRef, observation, receipt, or binding | no |
| exact external precondition or reference | an owner requires a foreign binding, capability, or policy fact but cannot manage its lifecycle | no |
| live cross-owner coordination | one result must initiate or admit, await, retry, cancel, recover, correlate, or settle several Composition-owned Invocations | yes |

A foreign reference grants no installation, availability, upgrade, lifecycle, credential,
admission, or effect authority. Ambient database access and implicit ownership inheritance remain
forbidden in every row.

### Avatar and Spectre

[Spectre](spectre/index.md) can own a generic VR Habitat and Encounter without Avatar. A Lich
Encounter may take one exact, already admitted Avatar `ProjectionBinding@1` as an external
precondition: Avatar still owns who and how appears, while Spectre owns the Habitat, participants,
comfort, interruption, and safe exit. The binding may still be live; Spectre cannot create, revise,
close, await, cancel, or recover it on Avatar's behalf. Both owners may later exchange attributed
terminal results without creating a circular dependency.

Use a Suite only when one live Product run must coordinate both owners—for example, admit a new
Avatar projection, await its settlement, open the Spectre Encounter, cancel both coherently, and
report honest partial completion.

### Companion and Familiar

[Companion](companion/index.md) requires a Familiar-backed device record while Familiar retains
embodiment, hardware capabilities, safety, and stop law. That requirement does not give Companion
physical authority. A Product that merely opens a mobile Companion session needs no Suite; one that
actively coordinates the conversation with a Familiar mission or real-world effect does.

### Workshop and Scavenger

**Mechanic** is proposed to package the Workshop candidate's passenger-vehicle service profile. A
part requirement may be handed to [Scavenger](scavenger/index.md) as an exact sourcing input without
moving diagnostic judgment or seller authority. A Suite is required only if the Product promises
one actively coordinated diagnostic-and-acquisition result with shared cancellation, ceilings,
recovery, and partial settlement.

### Voidlight, Riffmaw, Language Edition, and Broadcast

[Language Edition](language-edition/index.md) can build one language edition from an already-settled Broadcast script
and locked source master, an accepted Voidlight visual reference, and an immutable Riffmaw music
master without creating a Suite. Each reference retains its owner and grants no live lifecycle or
revision authority. Broadcast may later admit the settled Language Edition bundle into a new editorial
timeline the same way.

A Suite is required only when one Product promise must actively open and coordinate those new
Invocations—for example, request a visual correction, revise music, rebuild a language version,
cancel dependants coherently, and settle one aggregate publication result. A video model emitting
several modalities does not create that Suite; it creates one technical compound result whose
facets still need independent owner admission.

## Deployment and projection are different axes

| Term | Boundary |
| --- | --- |
| **Deployment profile** | an immutable eligible topology and configuration template; not an installation or service |
| **Deployment** | one configured installation of an exact Product revision for an operator, with concrete hosts, bindings, credentials, and policy |
| **domain projection** | an owner-governed read model of its own truth |
| **client projection** | presentation, platform integration, and bounded local interaction state; no application authority |
| **public projection** | a website, screenshot, report, or use-case explanation; publication evidence, never technical or delivery authority |

A new host, customer, or credential set normally creates another Deployment, not another Product.
A different interface normally creates another projection, not another Composition.

## Commercial catalogues and open-source Products

A commercial Product catalogue may live outside LychD and refer to exact public Composition or
Suite revisions. Its public website owns presentation, not LychD architecture, member truth, or
delivery state. LychD may link out; it should not copy private Product truth into technical docs.

An open-source Product reference may enter LychD's technical documentation only when it can name:

- an exact Product revision and supported use cases;
- exact eligible Composition or Suite revisions and owner-qualified profiles;
- source-code licence and notices, plus separate model, data, fixture, font, screenshot, mark, and
  redistribution rights where relevant;
- a reproducible installation and acceptance path;
- the evidence and delivery boundary recorded by State of Work; and
- externally supplied dependencies honestly, when the complete Product cannot be redistributed.

Public source alone is insufficient. If necessary weights, corpora, providers, or assets are not
redistributable, say “open-source Product code with externally supplied dependencies,” not an
unqualified FOSS Product. A Product becomes a technical reference only when State of Work records
the required evidence; this page creates neither a Product catalogue nor a selector.

For a new idea, use [Choosing a Home](choosing-a-home.md). For architectural law, continue with
[Workflow](../adr/28-workflow.md#compositions-products-suites-and-schedules). For delivery, judge
[State of Work](../state-of-the-work.md#composition-portfolio-delivery).
