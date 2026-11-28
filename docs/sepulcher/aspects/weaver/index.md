---
title: Spellweaver
icon: material/state-machine
---

# :material-state-machine: The Spellweaver

> _Through motion and silence, the thread remembers its course._

Once work has chosen a score, **Spellweaver** keeps it intact through execution, pause, return,
and ending. It is LychD's singular logical workflow jurisdiction: it validates immutable
**Scrolls** and admits their casting. Code and existing paths retain the short name `Weaver`.

## From Product to performance

A [Composition or Suite](../../../compositions/products-and-suites.md) publishes a score.
A **Pattern** gives its lineage a name, and a **Scroll** fixes one immutable revision. A
**Spell** names an action independently of that score. Each station places its exact contract,
whether the action calls an Agent, waits, delegates work, or produces an effect. Core's Bridge
and delegated rite predate the Portfolio and retain their original ownership.

An **Invocation** opens one bounded [Circle](../../../divination/altar/circle.md). Its
**Casting** performs the selected Scroll. The **Run** records that Invocation durably, including
the chosen score, so a worker returning from a pause can find the same revision. Graph advances
work between stations. In the [public-page score](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/workflows/webcrawler_chat.py),
the station `await_page_consent` binds to the Python node `AwaitPageConsent`. Its declared
edges allow the Run to wait, proceed to acquisition, or settle without contacting the page.
The score places that decision. The consent owner supplies the verdict. [Loom](../../../divination/altar/loom.md)
lets a reader inspect the declared topology.

A Product packages the application choice. A Suite can coordinate it by opening a parent Run
and separate Runs for its member Compositions. The parent correlates and settles their results.
Each member keeps its own records, judgment, consent, credentials, and effects.

[Pattern lifecycle](pattern-lifecycle.md#identity-before-motion) explains which revisions can be
inspected, selected for new work, or resumed from an existing Run. For example,
`delegated_rite@1` uses the effect-free reference adapter. Revision 2 pins an
[explicit runtime and profile](delegated-agents.md#pin-effective-configuration) for new admissions.
For application-selected workflows, including Creation and Scavenger, see the
[Portfolio delivery record](../../../state-of-the-work.md#composition-portfolio-delivery).

[ADR 28](../../../adr/28-workflow.md) distinguishes the designed package stores for Spell and
Scroll declarations from executable bindings, publication, and activation. The current
source-defined registry has no independent Spell catalogue or teaching surface.

## Choose a Bridge capability

In the Codex's `lychd.toml`, select the registered Bridge revision and the exact capability key
from your declared runtime inventory:

```toml
[weaver.bridge]
revision = "2"
capability_key = "my-runtime:chat:my-model"
```

Replace the example key with your runtime's key. It identifies the Animator, capability family,
and model together; a shared model name alone cannot pin a runtime. The selected capability must
support chat and tools. Loading Settings validates the selector's shape without contacting an
engine; Dispatcher checks the actual declaration, readiness, and policy at execution. An unknown,
incompatible, or unavailable target refuses the turn rather than choosing another runtime.

After restart, this configuration selects revision 2 for new Bridge admissions. Each Run records
its choice before queue publication and keeps it through hardware retries and consent pauses.
Later configuration changes or removal cannot redirect that Run or an idempotent retry. Without
the section, new turns use revision 1's eligible-pool selection; both revisions remain registered
for retained work. The key identifies a capability, not a model artifact or runtime configuration
fingerprint. The general Resolution Lock is a separate contract.

Revision 3 adds bounded public-note recall with transient Context injection and no tools. Its
[Archive configuration and authority checks](../../../divination/altar/bridge.md#public-note-answers) are separate from
revision 2's tool-capable conversation.

Revision 4 adds one explicitly declared public page, native consent and transient local-model
Context. Its [Webcrawler configuration](../webcrawler.md#public-page-answers) selects a qualified static
runtime and finite budgets. Neither profile turns a Scroll or source-authored text into tool authority.

Revision 5 adds read-only answers from the independently enabled Archive semantic generation,
without tools or earlier conversation history. Its [semantic generation configuration](../../../divination/altar/bridge.md#answer-from-a-semantic-generation)
binds the exact generation, explicit threshold and finite recall bounds to one exact local Chat
capability at boot. The selected Run retains that binding; opening the sources-only recall focus
does not change the configured casting.

### Prefer a ready route at admission

Revision 2 may instead rank exactly two declared local Chat routes:

```toml
[weaver.bridge]
revision = "2"

[weaver.bridge.preference]
schema_version = 1
routes = [
  { capability_key = "local-a:chat:model-a", weight = 9 },
  { capability_key = "local-b:chat:model-b", weight = 1 },
]
```

Replace both keys with literal identities from the declared inventory. Omit `capability_key`
from `[weaver.bridge]` when using `preference`; revision 2 accepts exactly one of them. Both
routes, including a disabled one, must declare local Soulstone Chat with tool support. Revisions
3, 4 and 5 retain their exact-key configuration and reject `preference`.

Weights are integer preferences from 0 through 1,000,000, with a positive total; they are not
traffic percentages, measured quality, or additional authority. Zero disables eligibility and
omits that route's retained phase and observation time. Admission directly refreshes each Animator
hosting an enabled route once, as a complete Animator batch, within one cooperative five-second
bound. That batch may include a disabled capability sharing the same Animator. After the batch, only observed-warm routes with unchanged declarations and
an unchanged, open admission generation remain eligible. Highest weight wins; an equal weight
uses ascending literal capability key. This observes readiness without activating a model,
preparing a grant or entering inference. Malformed or failed probes abort admission; a valid
non-warm observation excludes that route. An empty eligible set returns a content-free 503 code
before retaining a Run or user turn.

The admission decision becomes part of the Run: complete policy, digest, dated observations,
and one exact selected key. An idempotent replay returns it before any new probe, while changed
configuration applies only to new admissions. Execution and restart keep the key under the
existing Bridge tools, consent, and retry rules. The batch reserves no future readiness and
provides no execution fallback, so later unavailability may still pause or refuse execution.

The selected Run's Orb inspector shows these retained observations and exclusions. They describe
admission time, not current availability. Follow [configured Bridge casting](../../../state-of-the-work.md#configured-bridge-casting)
for the qualification boundary and [Dispatcher law](../../../adr/22-dispatcher.md) for the
selection and execution distinction.

## Follow the Scroll

Choose the route that matches the question:

- **[Discovery and router delegation](discovery.md)** follows scope branches, makes nested routes
  and workflows discoverable, and carries the selected routes into a bounded task handoff.
- **[Pattern lifecycle](pattern-lifecycle.md)** covers identity, manifests, admission,
  contribution, authorship protection, and revision continuity.
- **[Crucible](crucible.md)** covers two-round adversarial formation: declared biased Postures,
  independent first claims, attributed rebuttal, dissent-preserving synthesis, and the Magus Gate.
- **[Smith](smith.md)** applies bounded Inquiry at direction and construction
  scales, turns support and measure into bounded next steps, and follows local or delegated
  task handoffs through verification, target-owner effects, revision and retirement.
  [Assimilation](assimilation.md) applies it to foreign craft.
- **[Drift](drift/index.md)** evaluates an exact subject against a declared goal and returns
  evidence to the owner without granting routing or promotion authority.
- **[:material-autorenew: Ouroboros](ouroboros.md)** connects work, evaluation and training through
  correction, memory, Assimilation, Packaging and Evolution.
- **[Development bootstrap](development-bootstrap.md)** carries an operator-controlled coding
  campaign through evidence gates toward bounded native delegation and spare-capacity work.
  [Coding-runtime research](coding-runtime-research.md) compares the dated provider roads behind
  that procedure.
- **[Scheduling and service classes](scheduling-and-service-classes.md)** covers foreground,
  deadline-windowed, and spare-capacity admission, schedule time law, overlap, and explicit misses.
- **[Stasis and return](stasis-and-return.md)** covers Live and Durable Stasis, checkpoints,
  re-admission, terminal cleanup, and recovery limits.
- **[Execution roads](execution-roads.md)** covers the layered choice among native/local work,
  Portal-backed cognition, sovereign A2A tasks, delegated coding runtimes, and operator seats.
- **[Anonymization, taint, and egress](anonymization.md)** covers the local Privacy Cut,
  information-flow labels, Portal admission, quarantined return, and the boundary that makes
  subsidized remote reasoning usable.
- **[Delegated agents](delegated-agents.md)** covers the typed delegated station, `AgentJob`
  boundary, future CLI adapter acceptance, containment, and the present deterministic,
  no-network, effect-free reference adapter.

## Smith and its interpretation

**[Transmutation](../../../divination/transmutation/index.md)** in Divination examines the
Sephiroth correspondence: the relations that give an idea form, symmetry and reconstruction,
and life and the ending of forms. [Smith](smith.md) and [Ouroboros](ouroboros.md) keep the practical
procedures here in Spellweaver, with handoffs to evaluation and learning.

## Progressive craft without a mutable score

A Scroll may admit several explicit finish boundaries. A completed intermediate artifact can
begin a new forward Invocation; a terminal Run is never reopened to continue it.
[Pattern lifecycle](pattern-lifecycle.md#a-new-score-is-a-new-revision) distinguishes new input
from a changed score.

Under the Designed portable contract, a Scroll may require an exact model, profile, Provider, or
driver/dialect. The receiver-owned Resolution Lock closes remaining choices without weakening
those requirements and retains the selected bindings for the Invocation; an unavailable target
cannot silently become another runtime. Current Bridge exact-key selection provides the narrower
binding described above, not artifact or configuration fingerprinting. A Comfy graph is an
implementation preset, and a portable A2A Scroll remains inert until admitted. Follow
[Composition Suites](../../../compositions/products-and-suites.md#compositions-relate-without-nesting) when the
work needs live coordination across application owners.

## Hand off a bounded task

A [scoped context handoff](../../../adr/28-workflow.md#scoped-context-handoff) gives another Agent
a fresh Context for one bounded task while the coordinator keeps the wider purpose. For a
repository change, the packet includes the requested result, relevant operator decisions,
acceptance checks, allowed paths, source revision, dependencies, and scope routes to the owning
documents and code. The recipient reads those owners without inheriting the conversation that
produced the task.

If a needed decision is missing, the recipient requests that bounded input. It returns a candidate
patch or findings with verification evidence and unresolved questions for the coordinator to
assess. Merely loading another scope in the same conversation does not perform this handoff.

## The present score

[State of Work](../../../state-of-the-work.md) records local execution and the separate Stasis,
delegation, extension, and Loom delivery boundaries. Pattern
contribution and durable publication, scheduling, durable parallelism, compatibility and migration,
editing, authorship attestation, and protected-region admission remain undelivered.

Repository coding-agent choreography is separate: the
[tracked workflow playbooks](https://github.com/hexanomicon/lychd/tree/main/.agents/workflows) own
contributor procedure only, never Spellweaver or Pattern law.
