---
title: Delegated agents
icon: material/account-arrow-right-outline
---

# :material-account-arrow-right-outline: Delegated agents

> _The errand may leave the tower. The keys, the ledger, and the last word do not._

[Weaver](index.md) delegates through an attributed `AgentJob`. The coordinator tracks it; Graph
holds station state; the Run ledger binds its wait. An adapter receives a frozen request, never
the live Run, and the Pattern parks for one terminal adoption.

[ADR 28](../../../adr/28-workflow.md#parallelism-and-delegation) owns delegation law.
[Agents](../../../adr/20-agents.md#streaming-history-and-limits) owns the opaque-runtime boundary;
[Workers](../../../adr/14-workers.md#delegated-agentjob-labor) owns `AgentJob` labor.

## Seal the labor

| Type | Exact contents |
| --- | --- |
| `DelegatedAgentRequest` | `request_id` (idempotency key), `run_id`, `step_id`, `runtime`, `profile` (`read`, `candidate`, or `verify`), `prompt`, and `input_artifacts` |
| `DelegatedAgentJobRef` | `job_id`, `request_id`, `run_id`, `runtime`, and `profile`; it does not copy `step_id` |
| `DelegatedAgentJob` | `request`, `ref`, `status`, optional `result`, and ordered `events` |
| `DelegatedAgentResult` | Same `job_id`, terminal `status`, optional `output`, `artifacts`, and `error`; `failed`, `timed_out`, and `lost` require an error, while `succeeded` forbids one |

An `ArtifactRef` is frozen metadata for external bytes, not bytes or custody. The full station
contract declares containment, budget, timeout, cancellation, artifact boundary, and permitted
downstream use. Today's
`DelegatedAgentRequest` has no budget or timeout fields, and State records no measured delegated
budget ledger.

`DelegatedAgentRequest` and `ArtifactRef` are frozen from construction. The same
`request_id` and content returns the existing reference without another start; conflicting
content fails. [Pattern lifecycle](pattern-lifecycle.md) owns the pinned workflow context.

## Park for one job

`queued → admitted → preparing → running → succeeded | failed | cancelled | timed_out | lost`

This is the normal path; earlier states may take only their declared terminal edges. The station
stores `job_id`, GraphRunner snapshots, and the worker binds that owner with
`AWAITING_DELEGATE`. Only its terminal job may re-admit the Run.

First terminal adoption wins. Duplicate or late result adoption is inert and appends no event; a
mismatched job id is rejected, and an older job cannot resume a newer wait. Only `succeeded` lets
the delegated rite project optional text; every other terminal status fails it.

Reference cancellation is idempotent; no effectful process-tree cancellation is delivered.
`lost` records indeterminate external truth: it is terminal, neither polled nor retried, and not
permission to repeat. Cancellation during runtime start settles `lost`; another start exception
settles `failed`.

Resume-publication failure restores the exact wait under a fresh monotonic key. No startup
recovery exists for `AWAITING_DELEGATE`. A repeated callback may retry that restored wait; after
the admission CAS wins it is inert. [Stasis and return](stasis-and-return.md) owns re-admission.

## Keep the keys outside

The serialized envelope contains no `RunContext`, live toolsets, provider objects, leases,
credentials, or ambient authority. A profile and pure policy express posture; they do not prove
enforcement.

Returned text and `ArtifactRef`s are data, not authority. A lower-trust return remains
provenance-tagged and quarantined: it grants no instruction, execution, promotion, or effect
authority, only station-declared interpretation. A reference alone neither admits nor materializes bytes.
[Return quarantine](../../../adr/09-security.md#7-return-quarantine) owns this law.

If a delegated request, child provider call, or returned derivative may cross a remote boundary,
it also follows the parent [anonymization and egress](anonymization.md) contract. Delegation cannot
copy authority or shed privacy lineage.

This separation is also the delegation's economic leverage: the
[local anonymizer and bastion](anonymization.md#the-leverage-of-a-local-boundary) can make
subsidized remote cognition usable without making the remote runtime custodian of the raw
repository or its authority.

Provider-private commands and credentials stay behind the adapter boundary. Effectful foreign
labor additionally requires the Security-owned Coffin supervisor, job-scoped `nono` policy, and
Provider Gate; none belongs inside Pattern law. [The Coffin
profile](../../../adr/09-security.md#the-coffin-delegated-agent-profile) owns those boundaries.

## Name the delivered truth

Delegated execution is **Partial** in the [State of
Work](../../../state-of-the-work.md#delegated-agent-execution). The only runnable adapter is
`reference`: process-local, deterministic, and performing no model, filesystem, subprocess, or
network work.

Codex CLI (`codex-cli`), Claude Code (`claude-code`), and OpenCode Go (`opencode-go`) are
declared-only examples; none launches. No effectful
Coffin supervisor or CLI/provider process, credential isolation, or durable artifact custody is
delivered. Database shapes and a PostgreSQL store exist without a real PostgreSQL or migration
receipt or cross-process recovery.

The [tracked delegated-coding
playbook](https://github.com/hexanomicon/lychd/blob/main/.agents/workflows/delegated-coding.md)
records repository procedure and design input. It supplies neither runtime law nor delivery
evidence.
