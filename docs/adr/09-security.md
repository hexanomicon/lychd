---
title: 9. Security
icon: material/shield-lock-outline
---

# :material-shield-lock-outline: 9. Security

!!! abstract "Context"
    Security separates the secret-bearing Vessel, disposable execution, foreign delegated agents,
    and the host. It is a containment design for a trusted Linux kernel, rootless Podman, and the
    Magus's unprivileged host account; kernel/runtime escapes, hostile host administration, and
    compromise of that account are outside its protection.

## Decision: trust zones

| Zone | May hold | Must not hold |
| --- | --- | --- |
| Vessel | durable control-plane state, trusted provider and database authority | arbitrary shell/Python execution, writable trusted code |
| Tomb | a narrow execution-job hand and disposable child workspace | agent/LLM authority, provider or broad database secrets, host capability, Host Reactor access |
| Coffin | one foreign agent under one `AgentJob` and a revocable Gate bearer | queue/database credentials, promotion, authoritative VCS, host effects |

### 6. Tomb Execution Contract

The Tomb is deliberately non-agent: its child has a task-scoped workspace and artifacts, filtered
environment, zero network, outer-enforced resource limits, and complete-process-tree cancellation.
It requests data through its supervisor and reasoning through the Vessel's typed path. A Coffin is
not a more capable Tomb; it is its own delegated-agent boundary.

Rootless Podman maps the Pod with `UserNS=keep-id`; application units select `User=%U`, while the
Phylactery keeps the PostgreSQL image identity and a `:U,Z` data bind. This maps assigned paths,
not cross-service authority. Exact mounts, service credentials, and network policy remain the
boundary: lower-trust units receive no writable authoritative checkout, no whole Crypt, no
browser/keychain/home state, and no Podman socket. A host Reactor is a host boundary, never a
container capability.

Joined containers share localhost and routes, so a mount does not protect a reachable service.
Generated ports bind loopback, which is not authentication. Current local-only bootstrap authority
does not authenticate a hostile browser, peer, proxy, tunnel, or public endpoint; non-loopback
operation is refused until its remote identity and front-door contract exists.

Secrets remain references in Codex and Runes, are emitted only for a unit that needs them, and are
absent from lower-trust child environments, receipts, errors, and command lines. A Tomb supervisor
may receive only job claim/settlement database authority; a Coffin receives none.

### The Coffin Delegated-Agent Profile

A Coffin is one foreign runtime for one delegated occurrence. It needs an outer rootless service
boundary, inner job-scoped `nono` policy, and externally enforced resource ceilings. `read` gets an
immutable task projection; `candidate` gets a disposable copy-on-write or jj worktree. Workspace,
scratch, and artifacts are canonical, disjoint strict children of one job root, each granted once;
only `candidate` makes workspace writable. A `verify` specialization may add audited tools but may
not widen those roots or authorities.

The profiles return only analysis/bounded artifacts, a candidate patch/bounded artifacts, or
verification receipts respectively. They do not turn a provider name, blocked tool, failed test,
or expired budget into authority to widen a root, tool, network path, or credential.

The command is literal argv with a canonical absolute executable—no shell resolution, traversal,
controls, relative executable, or unbounded argv. Admission fails closed unless an attested `nono`
executable from the audited 0.66 series, Landlock ABI 6+, and the required filesystem, TCP, signal,
process, endpoint, environment-filtering, and outer resource-enforcement capabilities are observed.
Its environment is an allowlist, with known provider credential variables denied. Candidate output
stays quarantined pending trusted admission.

#### Provider Gate

The Provider Gate is the Coffin's sole network destination: one exact TLS port-443 destination and
admitted POST path, never a general proxy. Direct provider, registry, LAN, web, and other loopback
access is denied. The guest receives only a short-lived opaque or phantom credential; the real
credential and its reference remain in the trusted Gate.

A live grant binds bearer, job, provider, model, expiry, and monotonic request/token/spend budgets.
Cancellation, settlement, revocation, expiry, route mismatch, or budget exhaustion denies the
call. The Gate resolves a real credential only after this check. It cannot declassify content: its
grant, the Portal decision, and any admitted transformation must agree without widening one
another.

### Portal Privatization and Egress

[Context](21-context.md#privatization-and-the-privacy-cut) owns labels, influence lineage, the
Privacy Cut, and `TransformationReceipt`. Security owns declassification. The trusted Portal Egress
Gate issues an explicit typed `EgressDecision`, never inferred consent, binding the principal and
Sigil, Run/occurrence, provider/model/destination/purpose, canonical payload digest, labels,
policy revision, receipt, expiry, and allow/deny result. It settles before the first outbound byte;
changed payload, retry, resume, fallback, actor, policy, or destination requires another decision.

Consent cannot repair missing lineage, override a prohibited category, or broaden named content and
destination. On the `0.0` public-safe to `1.0` strictly-private scale:

- below `portal_threshold`, raw egress remains eligible under destination, purpose, and category
  policy;
- at or above `portal_threshold`, a satisfying Privacy Cut is required; and
- at or above `forbidden_threshold`, raw egress is forbidden.

Non-declassifiable categories remain forbidden regardless of weight, and a failed Cut fails
closed. Current local-only source has no hostile-network authorization and does not deliver this
general Portal gate; [State of
Work](../state-of-the-work.md#context-privatization-and-portal-egress) owns that boundary.

### 7. Return Quarantine

Tomb/Coffin stdout, artifacts, patches, and structured returns are untrusted bytes. They enter only
as provenance-tagged, instruction-fenced blocks in volatile Context layers; structural validation
does not grant them instruction authority. They are scanned for path and secret-scope violations,
but scan results do not execute commands or promote content. Promotion requires separate trusted
admission. The same quarantine applies to assimilated material and A2A returns.

### Refusal, compromise, and evidence

Missing containment, policy observation, revocation, credential separation, resource enforcement,
or audit receipt disables lower-trust execution. Suspected compromise revokes leases and Gate
grants, terminates or quarantines the process tree, quarantines workspace/output, taints associated
work, rotates credentials that crossed the supervisor boundary, preserves bounded secret-free
evidence, and requires trusted re-admission. Uncertain termination, revocation, or effect state is
not success.

Pure policy tests prove compilation, not containment. Containment needs effectful cross-boundary
receipts for mounts, environment and `/proc`, endpoints, descendant cancellation, ceilings,
credential absence, Gate races, quarantine, and recovery. Coffin/Gate policy exists; hostile
browser safety, effectful provider service, and host containment remain unclaimed according to
[State of Work](../state-of-the-work.md#delegated-agent-execution).

Audit records correlate the admitted job/occurrence, profile, roots, policy and receipt revisions,
Gate decision, measured ceilings, terminal classification, and quarantine handoff. A provider
status message or fluent completion is attribution, not a host-observed effect receipt.

At minimum, privileged host intents, secret provisioning or binding failures, Shadow dispatches,
policy denials, Portal egress and Privacy Cut decisions, and compromise quarantine or revocation
emit structured security events. [Observability](29-observability.md) owns their record shape and
retention.

## Consequences

An unavailable boundary is a refusal, not a reason to widen an execution profile. The current
policy shapes do not substitute for containment receipts. Once delivered, local transformation
and gated containment may admit lower-cost remote computation without handing its provider raw
authority-bearing context; economic advantage never relaxes a boundary.
