---
title: Workshop
icon: material/tools
---

# :material-tools: Workshop

Workshop keeps one technical service case legible from the first reported symptom to a scoped,
verified disposition. Its first service profile covers passenger vehicles; **Mechanic** is the
first Product that packages Workshop for that automotive user. The operator identifies the exact
vehicle, admits technical evidence, supplies observations or measurements, and receives the next
policy-admitted diagnostic-check proposal without mistaking fluent advice for professional authority.

This candidate study was reviewed on **2026-08-09**. It tests an application boundary, not a
new Extension Domain, accepted Portfolio membership, a registered Pattern, a delivered
Workshop path, or permission to inspect or repair a live machine.

The inert `src/lychd/compositions/workshop/` package reserves the candidate's canonical source
home. It exports no schema, service, registry contribution, Pattern or effect path; package
presence does not change the [Portfolio delivery boundary](../../state-of-the-work.md#composition-portfolio-delivery).

## Candidate contract

| Field | Candidate contract |
| --- | --- |
| **Identity** | `workshop.service` revision `1` |
| **Principal Pattern** | `workshop.service_case@1` |
| **First Product** | **Mechanic**, backed by the passenger-vehicle service profile rather than a separate Composition contract |
| **Begins with** | an admitted `WorkshopServiceRequest@1`, case-scoped asset identity and configuration evidence, reported condition, purpose, hazards, operator role, pinned service profile, attributed sources and observations, and authority and privacy ceilings |
| **Can return** | `WorkshopServiceDisposition@1`: scoped verified restoration, containment advice or attributable containment evidence, professional handoff, exact blocker, unresolved result, refusal, or indeterminate action |
| **Stops before** | emergency response, professional certification or statutory inspection, unsafe or unqualified work, autonomous machine control, guard or interlock bypass, unsupported part identity, purchase or payment, or declaring an asset generally safe from a conversational result |

`WorkshopServiceCase@1` owns only the service-case truth: purpose and assigned operator; exact
asset snapshot and its assurance; attributed symptoms, manuals, bulletins, schematics, fault
codes, images, statements and measurements; revisioned hypotheses and contradictions; proposed
checks, prerequisites, hazards, tools, results and interruptions; part or tool requirements; and
the final verification scope. Chat history is not that record, and a hypothesis never silently
becomes a fact.

## One workshop, versioned practices

`WorkshopServiceProfile@1` is a versioned rule set inside Workshop, not a new Core primitive. It
pins an asset ontology, identity and compatibility keys, acceptable sources, diagnostic checks,
units, tools, qualifications, hazards, verification recipes and stop rules. The first profile is
`workshop.automotive_passenger` revision `1`.

A tractor, CNC machine, boiler or appliance may later receive another profile only while it keeps
the same service-case truth and honest finish. A trade whose authority, records or recovery no
longer fit that contract earns another Composition and a typed handoff instead. A Product may
select the profile and its supported use cases; a client projection may change presentation, a
[Persona](../../adr/32-identity.md) may change voice and commitments, and an Agent Posture may
change one cognitive step. None carries technical or safety law.

## The guided case

```text
identify asset → triage hazards → admit evidence → revise hypotheses
→ request one discriminating check → wait for the operator → record the result
→ verify, advise containment, block, refuse, or hand off
```

An operator may open an intermittent no-start case from a phone, speak through explicit
push-to-talk, attach a fault-code report and finite images, then continue through a headset.
Workshop pins the exact configuration and applicable source release, then requests one
non-invasive, engine-off inspection with prerequisites, reason and stop conditions. The reported
result remains an attributed observation. If the evidence still conflicts, Workshop returns a
qualified handoff packet rather than guessing or prescribing live repair.

[Sight](../../sepulcher/extensions/prism/sight.md) may return an uncertain candidate connector
region; the mobile or glasses client projects it. The estimate proves neither component identity,
fault cause nor action safety. Future glasses remain another view of the same service case and
Composition. Silence, “seems fine,” an unobserved repair or an unacknowledged action cannot close
the case.

Revision one guides no vehicle lifting or support, exposed high voltage or other hazardous energy,
energized or rotating machinery, pressurized or combustible material, pyrotechnics, primary
vehicle controls, or guard and interlock defeat. It may organize evidence and prepare a qualified
handoff. Human consent does not manufacture competence, and local inference does not remove
access, retention, deletion or workplace privacy duties.

## Reuse beneath the Product

Workshop is the canonical reusable Composition; Mechanic is its first Product, not a duplicate
engine or a renamed Composition. Common workflow, authority, transport and memory boundaries
follow the Portfolio's [Product boundary](../index.md#products-package-compositions) and
[reuse law](../index.md#reuse-without-a-universal-helper).

| Existing office | What Workshop retains |
| --- | --- |
| [Communion](../communion/index.md), [Echo](../../sepulcher/extensions/echo.md), [Tether](../../sepulcher/extensions/tether.md) and [Ward](../../sepulcher/extensions/ward.md) | case purpose, object-specific application policy and field-conversation meaning—not capture, speech chronology, transport, authentication, grants or revocation |
| [Scout](../../sepulcher/extensions/scout.md) and [Sight](../../sepulcher/extensions/prism/sight.md) | source applicability, technical interpretation and a policy-admitted next-check proposal—not acquisition mechanics, pixels, regions or uncertainty |
| [Scavenger](../scavenger/index.md) | exact part need and acceptance evidence—not Bazoš listings, sellers, bargaining, commitment, payment or parcels |

The proposed typed seams remain Workshop-owned rather than new shared primitives:

| Projection | Minimum meaning |
| --- | --- |
| `WorkshopServiceRequest@1` | an asset owner or direct intake supplies purpose, case-scoped identity evidence, condition, hazards, operator role and ceilings |
| `WorkshopPartRequirement@1` | Workshop supplies compatibility, quantity, condition, certification and evidence needs to a stock owner or [Scavenger](../scavenger/index.md), without reservation or commitment authority |
| `WorkshopServiceDisposition@1` | Workshop returns outcome, verification scope, uncertainty, remaining hazards and evidence references; the asset owner retains return-to-service authority |

An asset owner such as [Homestead](../homestead/index.md) may eventually consume these projections
without giving Workshop its site, work order or controller envelope. A workshop stock owner may
provide a versioned snapshot and authoritative reservation, use or return receipts. Workshop
records those receipts against the case; it does not originate or mutate an ambient inventory.

## Honest settlement

Verified restoration means only that the case-defined symptom and acceptance checks passed under
recorded conditions; it is not blanket roadworthiness or certification. Containment advice is
still advice; containment evidence names the acting human or controller and independent
verification. A handoff carries identity, evidence, attempted checks, uncertainties and safety
notes. Missing identity, source, observation, tool, part, qualification or authority returns an
exact blocker; conflicting evidence or exhausted budget remains unresolved. An action with
uncertain acknowledgement is indeterminate and is neither repeated nor treated as complete.

A future proving slice should use a network-disabled synthetic passenger-vehicle case with
conflicting identity evidence, one pinned manual excerpt, finite images, one fault-code and
measurement sequence, and fake stock evidence. It must prove identity refusal, visible source
mismatch, one parked and resumed check without duplication, preserved Sight uncertainty,
evidence-driven hypothesis revision, hazardous-work handoff, a part requirement without purchase
authority, scoped verification, and interruption without invented completion. No live vehicle,
public web, camera stream, purchase, actuator or repair enters the fixture.

Related: [Composition Portfolio](../index.md) · [Homestead Maintenance](../homestead/maintenance.md)
· [Scavenger](../scavenger/index.md)
