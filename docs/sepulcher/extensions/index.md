---
title: Extensions
icon: material/hubspot
---

# :material-hubspot: The Federation of Extensions

> _Fifteen arts gather beneath one skin._

Search the web, judge an artifact, train a model candidate, carry a voice: different work needs
different organs. The fifteen **Extension Domains** below say where each responsibility belongs.
They map jurisdictions; a name on the map promises neither an installed package nor delivered
behavior.

## The Federation of Fifteen

| Name | Work it owns |
| --- | --- |
| [Oculus](oculus.md) | **Evidence and observability:** follow bounded observations, derivations, correlations and explicit gaps back to their sources. |
| [Tether](tether.md) | **Private reachability:** open exact private paths. |
| [Veil](veil.md) | **Hostile ingress:** terminate TLS and protocols, canonicalize metadata and admit declared routes. |
| [Ward](ward.md) | **IAM and authority:** resolve principals and recheck current permission over an exact object or effect. |
| [Spellweaver](weaver/index.md) | **Workflow:** validate Spell contracts and Scroll/Pattern lifecycle, admit castings and preserve continuity and logical time. |
| [Scout](scout.md) | **Web acquisition:** bound search, fetch, extraction, rendering and interaction. |
| [Smith](smith.md) | **Assimilation:** re-express admitted material as attributable candidate code. |
| [Soulforge](soulforge/index.md) | **Training:** bind admitted corpus, base digest, objective, Recipe, Training Run, evaluation and candidate-weight lineage. |
| [Drift](drift/index.md) | **Evaluation:** test exact subjects against declared goals through versioned trials and calibrated findings that retain uncertainty. |
| [Toll](toll.md) | **Economics:** distinguish quote, authorization, settlement, delivery, refund and reconciliation. |
| [Prism](prism/index.md) | **Visual and spatial grounding:** bind observations, transformations, reconstructions and generated forms to exact sources and derivatives, keeping them distinct. |
| [Echo](echo.md) | **Speech lifecycle:** carry capture, transcription, synthesis and delivery with origin, consent and outcome intact. |
| [Shadow](shadow/index.md) | **Possibility lineage:** hold isolated candidate worlds with exact parentage, evidence and terminal disposition. |
| [Mirror](mirror.md) | **Identity:** preserve Persona lineage, hydration provenance and attribution. |
| [Legion](legion.md) | **Distributed embodiment:** fence delegation across operator-owned bodies while each retains authority over its iron. |

Consider a source acquired for a candidate change. Scout can obtain the source, but acquisition
cannot establish its truth or authorize a wider use. Smith can prepare the candidate, Shadow
can hold an isolated alternative, and Drift can evaluate it. The responsible owner must still
judge whether it may become an effect; none of those contributors can promote its own conclusion
or grant privilege.

The same division holds at the system's edges. A private path or admitted route leaves application
authority with the service behind it. Oculus observes records without replacing their owners,
and Mirror attributes identity without authorizing the caller. Cooperation joins the offices
through these contracts.

## Domain, package, and provider

| Term | Place in the body |
| --- | --- |
| **Extension Domain** | One of the fifteen stable user-facing jurisdictions through which the Lich may grow |
| **extension package** | Explicitly selected built-in or private Crypt code admitted through `register(context)` and shaped stores |
| **Registrant** | Core or one selected extension package performing registration under a host-assigned `registrant_id` |
| **Contribution** | A typed addition admitted by one explicit receiving Core office or Extension Domain while that owner keeps authority |
| **Provider** | A concrete engine or service supplying mechanism behind a typed contract |

A package can register contributions with several Core offices or Domains. Conversely, one Domain
can receive several packages or Providers. These are different relationships, so **Activation**
must name a concrete package or declared instance rather than an abstract Domain.
[Compositions and Products](../../compositions/index.md) use and package the resulting contracts
while keeping their own responsibilities.

## How an organ enters

For a first contribution, follow [Extension authoring](authoring.md) through the existing Phoenix
registration shim, typed Rune, Quadlet contributor, and configuration test.

The coupled pre-v1 **Extension Protocol** admits explicitly selected built-in and private Crypt
packages through `register(context)`; it neither scans the environment nor discovers arbitrary
entry points. Built-ins evolve atomically with Core, while private packages accept refactor
breakage. A versioned independent extension-package API and conformance suite remain future work, so an
external protocol is the present boundary where process or lifecycle coupling is unacceptable.

After assembly, that selection stays fixed for the Vessel process. There is no hot-load,
hot-replace, or hot-unload. Changing code, package selection, dependencies, or contribution contracts
requires a new body generation under [Evolution](../../adr/18-evolution.md). Compatible Phylactery
records and explicit [Reanimation](../phylactery/reanimation.md) provide continuity into it;
volatile extension objects do not migrate. The boot boundary is enforced, while automated
Evolution remains Designed.

[ADR 05](../../adr/05-extensions.md) owns admission and compatibility. [State of
Work](../../state-of-the-work.md#extension-activation-contributions) records the five-store surface, its v1
capability attribution, and the remaining lifecycle limits. Selection grants shaped registration—not route, secret,
workflow, migration, workload, effect, or automatic activation authority.

## How an organ earns permanence

Authorship, tests, and evaluation produce a candidate and evidence for the target owner's
promotion decision. Smith, Shadow, and Drift cannot promote their own conclusions. Required HitL
or eligible policy supplies authorization; packaging, migration, activation, and verification
remain separately owned effects. Follow the [Assimilation passage](smith.md) to prepare that
handoff with its failures and uncertainty still attributed.

Automated Smith and Forge promotion is **Designed**, not delivered. [State of
Work](../../state-of-the-work.md#smith-forge-promotion) owns delivery; the [Assimilation
Covenant](../../adr/35-assimilation.md) owns the fuller passage from bounded candidate work to an
accepted organ.
