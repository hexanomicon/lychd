# Context-loading verification

## Trigger and acceptance

Use after introducing, moving, renaming, or changing a capability, contract, procedure, or context
route, and when auditing whether repository knowledge can be found. Load the task's matching
scope first; this check supplements its implementation or authoring workflow.

[ADR 01](../../docs/adr/01-doctrine.md#router-delegation) owns discoverability law;
[AGENTS.md](../../AGENTS.md#discovery-protocol) owns the coding-agent loading protocol;
[CONTRIBUTING](../../CONTRIBUTING.md#change-and-review-discipline) owns contributor reporting.
This playbook tests repository navigation, not runtime Context assembly or feature behavior.

Success means the task reaches the correct owner, applicable procedure, and relevant evidence
through maintained routes, with architecture and delivery distinguished. A correctly established
unsupported or unimplemented outcome can pass. Finding a plausible file or resolving a link is
insufficient.

## Prepare the question

The change author acts as evaluator. Before the discovery attempt, record:

- the revision and relevant working changes being checked;
- a realistic question in the caller's language, without target paths or an answer-bearing hint;
- the starting door: normally `AGENTS.md` for a coding agent, `CONTRIBUTING.md` for a contributor,
  or `docs/index.md` for a documentation reader; and
- the expected owning contract, procedure, evidence, and a small set of decisive distinctions
  that a plausible summary could lose, kept out of the discoverer's packet.

Cover the changed subject. When a shared router changes, add a neighboring task that should
still choose another branch. Include an ambiguity or unsupported premise when it could select
the wrong owner or turn a design into a delivery claim. Keep the set proportionate to the change.

## Follow the route

Use a reader or agent without the author's target knowledge when available. Give a platform
reader the question, starting door, allowed read boundary and a finite budget in a fresh context,
with no inherited author conversation, destination paths, patch, or expected answer. Request only
reading: no edits, network access, installations, feature execution, or promotion. Record actual
context exposure, workspace sharing and available tools; a read-only instruction does not enforce
an immutable workspace or containment. A manual author walkthrough is useful but must be labelled
as such.

If the probe launches a foreign coding runtime, apply [Delegated coding](delegated-coding.md),
including its enforced read-profile requirements. A platform reader in a shared checkout cannot
stand in as that immutable projection or as LychD containment evidence.

1. Read the entrypoint and complete matching scope; follow only relevant linked branches.
2. Record the ordered files and links followed, the scope choice, and why each search was needed.
3. Use the protocol's bounded searches when needed. If search rescues a missing trigger, index
   edge, stale path, or misleading link, record the defect rather than claiming route success.
   A focused symbol or test search inside an already routed source boundary is normal discovery;
   it does not require a hyperlink to every implementation file.
4. Answer from the owner. For behavior or delivery, identify its focused source, tests, lockfile,
   or maintained receipt and its limits. Do not run feature tests merely to test navigation.
5. Compare with the evaluator's expected owners. Investigate disagreement against canonical
   authority; do not make an incorrect expectation pass by adding a duplicate owner.
6. Assess answer fidelity separately from navigation: record which decisive distinctions were
   recovered, omitted, or contradicted. Reaching the right page does not establish that its
   qualifications survived the answer. An omission after reading the correct owner may be a
   synthesis failure; do not automatically repair the router for it.

Stop at the declared budget and report the last reachable owner and missing edge. Missing access
is an explicit unverified boundary. Discovery does not expand read permissions or resolve owner
conflicts by itself.

## Repair and repeat

Repair the smallest owning route: its task trigger, parent index, destination, or source/test
hook. Keep detailed routes with their deeper router; do not flatten the tree into `AGENTS.md` or
copy the answer into several pages. Resolve stale owners under the task's actual scope.

Repeat the failed question and affected neighboring case after repair. Prefer a new discoverer
for the rerun; otherwise report that the reader already knew the target. A fresh conversation
does not imply filesystem isolation. If interrupted, keep the partial trace and rerun against the
final candidate; do not reuse a verdict for bytes that changed afterward.

## Verification record

Retain in the change's review or handoff record:

| Question / starting door | Revision / working changes | Reader exposure | Observed route and searches | Result / gap / repair |
| --- | --- | --- | --- | --- |

Use **pass**, **route defect**, or **unverified**, with the authoritative answer and its limits.
Record route selection and answer fidelity separately, including the recovered and missing
distinctions; a successful route may still yield an incomplete answer.
Keep the before/after trace for repairs. This task-based check supplements local link/fragment
validation, `git diff --check`, the required architecture checks, and a clean documentation build
when published routes change. Those mechanical checks do not establish semantic findability.
