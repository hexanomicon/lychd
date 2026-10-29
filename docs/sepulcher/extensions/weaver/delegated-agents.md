---
title: Delegated agents
icon: material/account-arrow-right-outline
---

# :material-account-arrow-right-outline: Delegated agents

> _The errand may leave the tower. The keys, the ledger, and the last word do not._

A delegated task leaves its parent with a specific job to await. [Spellweaver](index.md) records
that task as an attributed `AgentJob`: the coordinator tracks the job, Graph holds station state,
and the Run ledger binds the wait. The adapter receives a frozen request rather than the live Run.
The Pattern then parks for one terminal adoption.

Today only the deterministic, effect-free `reference` adapter runs by default. Codex and Claude
have one-shot protocol adapters behind an unimplemented, refusing-by-default host port. Foreign
CLI execution, Coffin containment, and provider effects remain undelivered; [the delivered boundary](#name-the-delivered-truth)
below separates the current job mechanics from those designs.

[ADR 28](../../../adr/28-workflow.md#parallelism-and-delegation) owns delegation law.
[Agents](../../../adr/20-agents.md#streaming-history-and-limits) owns the opaque-runtime boundary;
[Workers](../../../adr/14-workers.md#delegated-agentjob-labor) owns `AgentJob` labor.

## Seal the labor

| Type | Exact contents |
| --- | --- |
| `DelegatedAgentRequest` | `request_id` (idempotency key), `run_id`, `step_id`, `runtime`, `profile` (`read`, `candidate`, or `verify`), `prompt`, and `input_artifacts` |
| `DelegatedCliRequestV2` | Explicit CLI schema/compiler, the occurrence/prompt fields, exact mechanical intent and qualified operator task/projection/custody/verification bindings; no positive authorization field |
| `DelegatedAgentJobRef` | `job_id`, `request_id`, `run_id`, `runtime`, and `profile`; it does not copy `step_id` |
| `DelegatedAgentJob` | `request`, `ref`, `status`, optional `result`, and ordered `events` |
| `DelegatedAgentResult` | Same `job_id`, terminal `status`, optional `output`, `artifacts`, and `error`; `failed`, `timed_out`, and `lost` require an error, while `succeeded` forbids one |

The frozen request can identify external material through an `ArtifactRef`, but that reference
contains metadata, not the bytes or their custody. The full station contract must also declare
containment, budget, timeout, cancellation, artifact boundary, and permitted downstream use.
Today's `DelegatedAgentRequest` has no budget or timeout fields, and State records no measured
delegated budget ledger. V2 adds the four existing capture/wall bounds and owner references; it
does not supply the full host/provider budget envelope or implement those owners. The actual
owner producer remains absent, and the trusted observation consumer denies by default. A positive
inert fixture proves only consumer conformance. [Workers](../../../adr/14-workers.md#versioned-cli-intent-and-owner-binding)
owns the exact version/codec, validity and compatibility contract.

Fresh legacy CLI requests refuse before host launch. Historical lookup and cancellation remain
readable at their original evidence scope; missing mechanics are never backfilled from current
settings. The published delegated score revisions retain their legacy requests. V2 currently
passes through inert callers and the existing store/coordinator, not a new published Pattern or
native Creation admission path.

`DelegatedAgentRequest` and `ArtifactRef` are frozen from construction. The same
`request_id` and content returns the existing reference without another start; conflicting
content fails. [Pattern lifecycle](pattern-lifecycle.md) owns the pinned workflow context.

## Park for one job

`queued → admitted → preparing → running → succeeded | failed | cancelled | timed_out | lost`

This is the normal path; earlier states may take only their declared terminal edges. The station
stores `job_id`, GraphRunner snapshots, and the worker binds that owner with
`AWAITING_DELEGATE`. Only its terminal job may re-admit the Run.

The first terminal adoption settles the job's return. Duplicate or late adoption is inert and
appends no event. A mismatched job id is rejected, so an older job cannot resume a newer wait.
Only `succeeded` lets the delegated rite project optional text; every other terminal status fails
that rite.

Reference cancellation is idempotent; no effectful process-tree cancellation is delivered.
`lost` records indeterminate external truth: it is terminal for result adoption, neither polled nor
restarted, and not permission to repeat. It is also not containment proof. Explicit parent
cancellation still calls the owning runtime's cancellation operation and records
`lost → cancelled` only after that call returns. Cancellation during runtime start settles `lost`.
An unclassified exception after `runtime.start` is invoked also settles `lost`; a failure before
invocation may settle `failed`.

Resume admission atomically creates the fresh monotonic delivery key. Publication failure leaves
that exact queued delivery for relay. Startup recognizes the pre-park crash window only when the
first resumable checkpoint binds the same Run and delegated job; otherwise it contains correlated
jobs before parent failure. It refreshes durable delegated waits and re-admits only the terminal job
that owns each wait; missing coordination or owner identity fails required PostgreSQL startup.
After the admission CAS wins, repeated callbacks are inert.
[Stasis and return](stasis-and-return.md) owns re-admission.

## Keep the keys outside

The serialized envelope contains no `RunContext`, live toolsets, provider objects, leases,
credentials, or ambient authority. A profile and pure policy express posture; they do not prove
enforcement.

The station may interpret returned text and `ArtifactRef`s only as its contract declares. A
lower-trust return remains provenance-tagged and quarantined; it grants no instruction, execution,
promotion, or effect authority. Even a reference to bytes neither admits nor materializes them.
[Return quarantine](../../../adr/09-security.md#7-return-quarantine) owns this law.

The host marks candidate content produced through this job lineage `agent_generated`; a later
human approval does not relabel it. When a candidate touches a [Protected
Region](../../../adr/28-workflow.md#authorship-provenance-and-protected-regions), promotion follows
the exact live Gate in [Pattern lifecycle](pattern-lifecycle.md#human-attested-material-stops-at-a-gate).
The delegated runtime never receives the authority to alter or erase the target-owner manifest.

If a delegated request, child provider call, or returned derivative may cross a remote boundary,
it also follows the parent [anonymization and egress](anonymization.md) contract. Delegation cannot
copy authority or shed privacy lineage.

A runtime and its child provider receive different disclosures. The remote runtime gets its
minimum workspace projection under a `DelegatedRuntimeTarget`. The child model requires a fresh
`PortalTarget` decision for its exact prompt/tool envelope. When transformation policy requires
it, that child disclosure also gets a second, consumer-specific Cut. A local Coffin must still protect the host from its
runtime even when only that child call crosses the network. The outer `AgentJob` never authorizes
an unknown series of child payloads.

This separation is also the delegation's economic leverage: the
[local anonymizer and bastion](anonymization.md#the-leverage-of-a-local-boundary) can make
subsidized remote cognition usable without making the remote runtime custodian of the raw
repository or its authority.

Provider-private commands and credentials stay behind the adapter boundary. Effectful foreign
labor additionally requires the Security-owned Coffin supervisor, job-scoped `nono` policy, and
Provider Gate; none belongs inside Pattern law. [The Coffin
profile](../../../adr/09-security.md#the-coffin-delegated-agent-profile) owns those boundaries.
A runtime that cannot use the exact Provider Gate endpoint, disclose its child model route, or
disable ambient network/fallback is ineligible. Transparent MITM is not an adapter.

## Wrap a CLI as a bounded adapter { #cli-adapter-passage }

Creation's [CLI branch](creation.md#cli-delegation-branch) uses this job boundary for a concrete
engineering assignment. The wrapper is a deterministic protocol adapter under a supervisor:
it translates an admitted task into one runtime invocation and translates observed termination
into a result. A separate native Agent may prepare or review that task. The wrapper does not
become another sefirah, coordinator, or source of permission.

An effectful adapter needs these five passages under the existing Coffin contract:

1. **Prepare.** Pin the base, task projection, allowed paths, runtime/adapter versions, output
   contract, limits, and authorized downstream use. Resolve effective configuration explicitly,
   including hooks, plugins, MCP servers, and continuation state; arbitrary project or user
   configuration must not expand the task. Apply the [Privacy Cut](anonymization.md#preserve-the-coding-question)
   when the chosen recipient requires transformation. Required governing instructions still reach
   the worker in its admitted packet.
2. **Launch.** Use an absolute executable and bounded argument vector, with task text supplied as
   data rather than interpolated shell code. Bind the provider session and supervised process to
   the job when observable. Attest workspace, environment, credentials, outbound calls, and resource
   boundaries before invoking an effectful runtime. Prompt instructions or CLI tool permissions
   alone do not establish this containment.
3. **Observe.** Parse the versioned machine event protocol, keep diagnostics distinct, and bound
   both streams. Preserve ordering, partial results, and capture gaps. An unknown usage count is
   unknown consumption, not a zero-cost receipt. Provider tool events remain attributed claims
   unless the trusted host independently observed the stated operation.
4. **Settle.** Correlate the terminal protocol record, process outcome, job identity, and retained
   artifacts. Truncated output, an unresolved child, or an ambiguous start cannot become success
   from the last sentence alone. Cancellation and timeout require the supervisor's full descendant
   settlement evidence; apply the existing `lost` and reconciliation rules when effects remain
   uncertain. Never start another attempt merely because the response was lost.
5. **Return.** Collect bounded candidate bytes under host custody, check allowed paths and base,
   and quarantine them separately from narrative and provider events. Use declared rehydration
   positions only; a raw patch is not a general substitution template. Independent local review
   and verification examine the exact resulting candidate. Adapter success neither passes those
   checks nor promotes the artifact.

Begin an adapter by defining how its observed events and exit conditions map to the existing job
statuses. A non-zero exit cannot automatically mean `failed`, because work may already have
occurred. Establishing that nothing started requires an adapter-specific rejection receipt;
uncertainty cannot establish it. The current request/result types provide a starting envelope,
not evidence that this richer binding, budget accounting, or artifact custody already exists.

The current protocol implementation pins Codex 0.159.2 and Claude Code 2.1.296. It builds literal
commands with prompt bytes on stdin, isolated configuration roots and an allowlisted replacement
environment, then parses bounded JSONL. Incomplete lines, malformed or duplicate terminal evidence,
oversized output, and success paired with a failing process exit remain `lost`. Raw provider errors
and stderr do not enter retained diagnostics. Polling receives the store-retained request; V2
independently compiles its complete expected launch specification and limits before comparing the
host result and matching receipt. Historical legacy lookup correlates only its original request
and deterministic stdin. Cancellation needs the same retained interpretation and matching
whole-job containment receipt, including before the first poll. Neither operation re-admits or
launches work, even after owner-observation expiry. Claude accepts a reviewed core event subset with one initialized session; unknown
event variants refuse until their envelopes and ordering are reviewed.

No host implementation or authentication bridge ships, and neither adapter is automatically
registered. Security requires an exact audited source/policy/executable qualification with
applicable advisories dispositioned; a version number, CLI help and advertised limits do not
qualify a host. [Containment version selection](coding-runtime-research.md#containment-version-selection)
explains why the former series baseline was retired without admitting a replacement. The required
outer service, network, resource, credential, Gate and artifact boundaries must all be proved
before any real launch.

### Compare actual integration surfaces { #cli-integration-references }

The following primary documentation was checked on 2026-10-12 for this design. It supplies implementation
leads, not LychD acceptance receipts or a reason to adopt a provider's default permissions.

| External surface | Useful mechanism | LychD still has to establish |
| --- | --- | --- |
| [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode) | `codex exec --json` emits JSONL events; `--output-schema` requests a structured final result. | Exact event/terminal interpretation, effective configuration, artifact custody, and host verification. |
| [Codex app-server](https://learn.chatgpt.com/docs/app-server) | Bidirectional stdio JSONL supports explicit approval requests, thread/turn identity, and interruption. | Pin the binary's generated protocol schema and admitted methods; exclude `thread/shellCommand` and experimental `process/*`, which run outside its sandbox. |
| [Claude Code programmatic mode](https://code.claude.com/docs/en/headless) | Print mode offers JSON, streamed events, and schema-constrained output. `--allowedTools` controls auto-approval; bare mode limits ambient discovery. | Tool availability and OS containment separately; required task context; pinned behavior when schemas, streams, or background work fail. |
| [Claude Agent SDK configuration](https://code.claude.com/docs/en/agent-sdk/configuration) | Explicit settings sources, tools, model, turn limits, and spending limits configure its runtime loop. | Python's `env` merges with the inherited environment; supply a clean supervisor environment rather than assuming a small dictionary removes secrets. |
| [nono's D-Bus advisory](https://github.com/nolabs-ai/nono/security/advisories/GHSA-27vp-2mmc-vmh3) | A documented local IPC escape in CLI profiles before the listed fix demonstrates why a sandbox name is insufficient. | Current patched implementation and policy, with negative tests for host IPC and descendant escape on the admitted platform. |

For the first bounded job, prefer one machine-readable invocation over terminal scraping. Use
app-server when approval and continuation require a bidirectional protocol. Each runtime keeps a
thin adapter; the supervisor, Provider Gate, budget accounting, and artifact admission remain
shared owners. This is an implementation recommendation, not a selected or installed runtime.

### Pin effective configuration

Current Settings accepts one exact delegated casting selection:

```toml
[weaver.delegation]
revision = "2"
runtime = "reference"
profile = "read"
```

This executable example selects the inert reference runtime through `delegated_rite@2`. Omission
keeps revision 1. Another runtime must already be explicitly registered; an unknown name refuses
assembly. New admissions retain the selected runtime/profile in Run intent and checkpoints.
Changing configuration or retrying an idempotency key does not redirect an existing Run.
The selector supplies no host, privacy, provider or execution authority.

There is no `claude`, `codex_cli`, `fallback`, or `anonymization` activation switch. Unknown
fields are rejected. A future effectful selection must also retain its effective configuration
with the job: runtime and protocol revision, model and Gate endpoint, isolated configuration and
session roots, available tools, hooks/MCP/plugins, allowed environment, output contract, and finite
time, token, spend, process and artifact limits. A resumed job retains that selection; changing
operator settings does not rewrite an admitted occurrence.

Disable implicit provider fallback in each harness. A configured alternate belongs to the pinned
[execution-road policy](execution-roads.md#failure-stays-on-the-score), with separate privacy,
destination and budget admission. A timeout after submission requires reconciliation before an
alternate can start. Even a same-model retry is another physical disclosure: Claude's documented
[gateway protocol](https://code.claude.com/docs/en/llm-gateway-protocol) can retry with changed request
fields, so a retry label cannot establish identical bytes. Test every child request at the Gate.

Supported account integration is a separate compatibility decision. OpenAI documents an
[app-server plan-usage integration](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server);
its existence does not admit a LychD route or authorize copying an operator's login store. Bind any
future supported account flow to its actual application, entitlement and credential custodian.
[Portal Roads](../../animator/portal-roads.md) retains the current direct-server-API starting point.

### Prepare the adapter before remote labor { #cli-adapter-acceptance }

Complete the capability in independently reviewable slices:

| Slice | Evidence needed before advancing |
| --- | --- |
| Protocol and result normalization | Recorded synthetic streams exercise success, explicit rejection, malformed/truncated output, duplicate terminal events, mismatched identity, and oversized diagnostics. No model or foreign executable is needed. |
| One contained local runtime | Observe denied out-of-scope reads/writes, unavailable host sockets and credentials, bounded output, complete cancellation, and reconciliation after an ambiguous launch. CLI flags alone are insufficient. |
| Admitted provider crossing | Verify the exact destination and payload, applicable Cut and utility evidence, and every child call's gate; block an undeclared retry or fallback. |
| Creation candidate return | An exact patch or artifact survives quarantine, any permitted rehydration, and independent checks against the real base. A useful proposal can still fail acceptance. |

Test the boundary with returns that look successful while violating its contract: a process that
prints success before failing, a valid result whose artifact belongs to another job or base, a
background child that outlives its parent, and a patch outside the admitted workspace. Pair these
adversarial checks with successful controls so refusal cannot masquerade as a working adapter.
The bounded protocol slice has offline tests; contained execution, provider crossing and
candidate custody still need their own acceptance evidence.

## Name the delivered truth

Delegated execution is **Partial** in the [State of
Work](../../../state-of-the-work.md#delegated-agent-execution). The only runnable adapter is
`reference`: process-local, deterministic, and performing no model, filesystem, subprocess, or
network work.

Codex CLI (`codex`) and Claude Code (`claude`) have unregistered protocol adapters whose default
host refuses execution. OpenCode Go (`opencode-go`) remains a declared-only example. No effectful
Coffin supervisor or CLI/provider process, credential isolation, or durable artifact custody is
delivered. Database shapes and a PostgreSQL store exist without a real provider or two-process
PostgreSQL recovery receipt; exact pre-park recovery is proved only with focused in-memory tests.

The [tracked delegated-coding
playbook](https://github.com/hexanomicon/lychd/blob/main/.agents/workflows/delegated-coding.md)
records repository procedure and design input. It supplies neither runtime law nor delivery
evidence.

[Execution roads](execution-roads.md) owns when this job form is preferable to a native Portal
call or sovereign A2A task.
