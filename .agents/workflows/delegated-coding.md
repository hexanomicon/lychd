# Delegated Coding

## Trigger and maturity

Use this playbook when a LychD Pattern or an operator-controlled campaign hands bounded repository
labor to Codex CLI, Claude Code, OpenCode, or another foreign coding runtime.

This is current repository procedure and a design input for later LychD operation. It is not
evidence that an effectful runtime adapter ships.
[State of Work](../../docs/state-of-the-work.md#delegated-agent-execution) owns that boundary;
ADRs 09, 14, 24, and 28 own containment, job, Graph, and Pattern law.

## Admission preflight

Current LychD ships no effectful Coffin adapter. An operator-controlled campaign may use a
platform-provided coding agent only under the platform's observed permissions; that is not a
LychD containment receipt.

Before any foreign runtime launches, record the actual enforcement for workspace roots, tools,
network, environment and credentials, resource ceilings, process-tree cancellation, artifact
custody, and terminal settlement. Apply the requirements of the selected profile even when its
name is `read`: immutability alone does not prevent disclosure or egress. Refuse the launch when
any required ADR 09 boundary is unavailable or cannot be observed. The in-process, effect-free
reference adapter launches no guest and may exercise state transitions without this foreign-runtime
preflight; it cannot stand in as evidence that the boundary exists.

## Request contract

A delegated coding request pins one truthful identity envelope:

- a LychD `AgentJob` pins parent Run, step, request, and adapter identity; or
- an operator campaign pins its actual campaign, task, worker session, and runtime identity.

It never invents a LychD Run or adapter identity for work performed outside that ledger. Both
envelopes also pin:

- immutable base revision and task-scoped input artifacts;
- exact prompt, acceptance target, non-goals, and allowed paths;
- `read`, `candidate`, or `verify` containment profile;
- permitted tools and effects;
- time, tokens, spend, CPU, memory, process, disk, and artifact ceilings;
- cancellation and terminal-result contract; and
- the downstream use allowed for returned artifacts.

Provider names never imply authority. A Pattern names a typed adapter, not a shell command,
credential, provider-private planner, or subagent topology.

## Context hierarchy

The parent owns purpose and assembles the smallest sufficient packet. The delegated runtime may
plan privately, but LychD relies only on admitted outputs and observable boundary evidence.

For multi-agent work:

1. one informed Lead reads canonical owners;
2. children receive closed, role-specific packets;
3. proposal, review, and repair use separate contexts when self-judgment would matter;
4. the parent retains global budget, ordering, and acceptance; and
5. child output returns as a candidate artifact, never as promoted truth.

Hidden chain-of-thought is neither requested nor treated as evidence.

## Workspace and effects

- `read` receives an immutable projection and returns analysis or bounded artifacts.
- `candidate` receives a disposable copy-on-write/worktree surface and returns a candidate patch.
- `verify` may add audited tools without widening roots, secrets, or promotion authority.

The job receives only task workspace, scratch, and artifact roots. It receives no authoritative
checkout write, broad home, Codex, Crypt, queue/database credential, provider key, browser
session, infrastructure mutation, or deployment authority.

External data and model-provider access cross typed host gates. The guest never converts a missing
tool, blocked network path, failed test, or expired budget into permission to widen itself.

## Subsidized compute path

When lower-cost provider capacity motivates delegation, record price and capacity as selection
factors—not authority. The admissible path is:

1. build the smallest useful task projection locally;
2. run deterministic censorship and local semantic anonymization;
3. reject the offload if sanitization destroyed identifiers, dependency relations, or diagnostics
   required by the task;
4. bind the exact sanitized payload, destination, model, expiry, token ceiling, and spend ceiling;
5. transmit only through the observed local bastion: Coffin supervision, Portal Egress Gate, and
   Provider Gate; and
6. quarantine the return, then rehydrate permitted placeholders, test against the real checkout,
   and admit selected bytes locally.

The raw checkout, credential, identity map, pseudonym map, and promotion authority do not become
the price of a cheap call. Until LychD delivers and attests this path, an operator campaign may
record only the platform boundaries it actually observes; it must not claim a LychD containment
receipt.

## Settlement and recovery

A LychD delegation keeps `AgentJob` state and the parent Graph wait explicit. An operator campaign
keeps the equivalent task/session record under its actual coordinator. In either case, the first
admitted terminal result wins; late results are inert. Cancellation or timeout must settle the
full process tree.

Treat `LOST` or an ambiguous external outcome as unknown. Do not repeat an effectful occurrence
until its workspace, processes, remote effects, artifacts, and idempotency identity have been
reconciled. A retry receives a new occurrence identity unless the owning protocol proves safe
re-admission of the original.

Returned claims are classified:

- patch/artifact bytes;
- tool and test receipts observed by the host;
- provider-reported trace or status; and
- analysis or recommendation.

Only the first two can become direct implementation evidence, and only after trusted admission
checks. A fluent completion message is not a receipt.

## Handoff

Foreign text, patches, filenames, logs, and artifacts remain attributed untrusted data. Preserve
their provider/job provenance, fence embedded instructions from the review context, scan for
secrets and out-of-scope paths, and inspect candidate changes in a disposable surface. Never
execute a returned command or accept a requested authority expansion merely because it appears
inside an artifact.

Only after that quarantine does the parent inspect the candidate against the exact base, owners,
allowed paths, and acceptance gates and admit selected bytes into a trusted patch. It reports
changed behavior, artifacts, checks, ambiguous effects, and unrun live evidence. Promotion,
merge, publication, deployment, and cleanup remain separate decisions.
