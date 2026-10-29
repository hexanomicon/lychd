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
| Gateway Host | edge certificates and routes, local defense-in-depth firewall intent, one backend service credential, optional tunnel key, bounded transport evidence | database or application authority, private Context, provider credentials, Sigils, corpus, general LAN route, ingress-derived host administration |
| Platform edge | one platform credential, service credential, bounded transport/effect journal, and typed adapter | provider/database credentials, corpus, private Context, policy, home Sigil, arbitrary home route or host administration |
| Tomb | a narrow execution-job hand and disposable child workspace | agent/LLM authority, provider or broad database secrets, host capability, Host Reactor access |
| Coffin | one foreign agent under one `AgentJob` and a revocable Gate bearer | queue/database credentials, promotion, authoritative VCS, host effects |

A [Gateway Host](../sepulcher/gateway.md) is an optional separate ingress placement, not an
Extension Domain, Composition, caller, or second authority plane. Veil owns its admitted routes;
Tether may supply an exact private road; the receiving Ward and application still authenticate
and authorize every request. The Core host accepts only the named backend flow from the Gateway
identity. Policy outside the Gateway host—a router/firewall, L3-switch ACL, or cloud-network rule,
together with the receiving Core firewall—enforces the zone's public listener and exact backend
flow. Rules controlled only by the Gateway itself are defense in depth and cannot prove containment
after host compromise. A same-host proxy is Veil but not a Gateway Host. Operator administration
uses a separate infrastructure path whose credential is unavailable to ingress and backend
workloads.

Gateway compromise closes the route, revokes edge certificates, backend and tunnel credentials,
fences its deployment generation, quarantines bounded transport evidence, and rebuilds the host.
It does not justify rotating disjoint Core credentials unless evidence shows they crossed, and it
never upgrades forwarded identity or authorizes an effect.

A remote platform edge translates an application's platform traffic. Its assertions alone cannot
authorize a caller: where upstream events lack an independently verifiable end-user signature,
a compromised edge can fabricate that evidence. Enrolled/private Context and consequential
effects therefore require independent proof presented to Ward. On edge compromise, revoke
platform, workload, tunnel, and edge-epoch credentials, quarantine the journal, and reconcile
external identities. Disjoint home/provider credentials are implicated only if boundary evidence
shows they crossed.

### Tomb Execution Contract {#6-tomb-execution-contract}

The Tomb is deliberately non-agent: its child has a task-scoped workspace and artifacts, filtered
environment, zero network, outer-enforced resource limits, and complete-process-tree cancellation.
It requests data through its supervisor and reasoning through the Vessel's typed path. A Coffin is
not a more capable Tomb; it is its own delegated-agent boundary.

Rootless Podman maps the Pod with `UserNS=keep-id`; application units select `User=%U`, while the
Phylactery explicitly selects `User=postgres` and a `:U,Z` data bind. This maps assigned paths,
not cross-service authority. Exact mounts, service credentials, and network policy remain the
boundary: lower-trust units receive no writable authoritative checkout, no whole Crypt, no
browser/keychain/home state, and no Podman socket. A host Reactor is a host boundary, never a
container capability.

Joined containers share localhost and routes, so a mount does not protect a reachable service.
Generated ports bind loopback, which is not authentication. The local operator must also present
a dedicated high-entropy HTTP Basic credential before receiving the fixed local Sigil. The
credential belongs only to the Vessel and the host operator; shared Pod membership grants no
access. Unsafe requests with a foreign Origin are refused even when their CSRF token is valid.
This local credential does not establish remote identity, object isolation, or effect-time
revocation. Dedicated-profile browser operation remains subject to its acceptance evidence.
The [isolated developer fixture](11-backend.md#isolated-developer-fixture-designed) may use its
configured loopback Vite proxy while retaining the same authentication, Host, CORS, Origin, and
CSRF checks. Peer access, production access through a proxy, tunnels, and non-loopback operation
remain refused. The raw SAQ administrative UI is disabled: its traceback and broker-mutation
surfaces are not admitted operator projections.

### Local installation-stop admission

The former `native-owned-lifespan@1` host-Vessel stop profile and its HTTP admission route are
retired with native deployment. Historical signed-stop receipts remain dated observations of
that removed profile; they cannot authorize a current container operation.

A future container lifecycle port must authenticate exact installation intent, retain current
binding and process/container authority, close admission before retirement, and independently
verify the owned terminal outcome before stopping dependencies. Unknown, lost or forced outcomes
preserve dependencies for reconciliation. No native-profile rename, inactive unit alone, successful
manager reply or direct fallback can establish that contract. Current active-Vessel lifecycle
operations refuse until that passage is implemented and qualified.

Ordinary local HTTP Basic, Host, Origin, CORS and CSRF boundaries remain authoritative. Retiring
the special stop route removes its middleware exceptions; it creates no replacement bypass.

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
controls, relative executable, or unbounded argv. Admission fails closed unless a reviewed
qualification binds the exact `nono` source revision and patchset, dependency lock/build inputs,
canonical executable digest, selected policy and outer runtime, and target platform to an audit
receipt and an explicit disposition of applicable security advisories. A version string, moving
series, latest release or upstream audit sponsorship establishes none of that closure. Applicable
known defects require inspected fixes and regression evidence; an excluded mechanism requires
justified, enforced non-applicability. Unknown fix status, provenance or applicability refuses.

The former 0.66-series baseline is retired: later upstream advisory ranges include it. Neither a
downgrade to that series nor a newer release is admitted by this amendment. The
[dated containment study](../sepulcher/extensions/weaver/coding-runtime-research.md#containment-version-selection)
keeps the primary-source findings and their limits. Landlock ABI 6+ and the required filesystem,
TCP, signal, process, endpoint, environment-filtering and outer resource-enforcement capabilities
must still be observed for the exact profile. Requested limits are not measured ceilings. Its
environment is an allowlist, with known provider credential variables denied. Candidate output
stays quarantined pending trusted admission. No executable or host profile is qualified here.

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
Privacy Cut, transformation evidence, and Cut verification. Security owns declassification for
every remote disclosure, not only model calls. The trusted Portal Egress Gate is the first
implementation name for this general byte-time boundary.

#### Target and disclosure basis

`EgressDecision` carries one tagged `RemoteTarget`:

- `PortalTarget` binds the actual recipient provider/service, operation, model when applicable,
  and a protocol-specific endpoint: canonical origin and exact request target for HTTPS, or
  fixed resolver protocol, literal endpoint and exact question for DNS. It also binds an
  immutable custody-route digest when an intermediary exists;
- `A2ATarget` binds the enrolled peer Principal, public task schema, adapter revision, and canonical
  origin; and
- `DelegatedRuntimeTarget` binds the foreign runtime, containment profile, job, adapter revision,
  and destination when the runtime itself is remote.

It also carries one tagged `DisclosureBasis`: `RawEligible` binds the exact classification,
category, target, purpose, and policy facts that make untransformed bytes eligible;
`CutEvidence` binds the exact `PrivacyCut@1` instance/digest, final candidate digest, terminal
transformation-receipt-chain digest, and `CutVerification@1` digest. A nullable Cut revision or a
transformer claim alone is not an admissible privacy basis. The Gate verifies that this basis,
candidate/wire digest, target, purpose, policy, expiry, and remaining disclosure use all agree.

An HTTPS site's identity is distinct from the native Scout adapter implementing the contact.
DNS resolution and TLS hostname disclosure precede the HTTP request and need their own admitted
handoffs; a resolver decision cannot authorize the site. DNS custody includes the selected
resolver's forwarding or recursive-resolution policy. A fixed resolver address does not establish
that policy, and unknown custody facts refuse whenever disclosure policy depends on them.

The [trusted local Scout profile](38-iam.md#trusted-local-scout-profile) may admit an explicit
public-locator declaration from an authenticated operator separately authorized to classify that
source. The declaration binds the exact complete URL, subject and authentication generation,
purpose, source/influence manifest, classification, category and policy revision. It is an
attributed operator assertion, not a proof of publicness. The host verifies this basis before
issuing `RawEligible`; authentication, public reachability and the subsequent consent click do
not supply classification. Ordinary chat, model output or copied Context cannot inherit the
declaration merely by containing the same URL. Missing lineage, known restricted influence and
prohibited categories retain the refusal rules below.

The [outbound public-text peer profile](26-a2a.md#peer-task-jsonrpc-1) has a separate dedicated
operator-authored-text source adapter. It requires actual local authentication and a distinct
current classification action, and binds the exact complete text, source/influence facts,
category, purpose, enrolled target and policy generation. This is an attributed assertion of
publicness, not a PII detector or proof of original authorship. Known restricted ancestry,
unknown lineage, prohibited categories and local-only constraints still refuse. Text equality,
ordinary chat, ASR, model output and a serialized declaration cannot supply this authority.

Each child provider request from a coding runtime needs its own `PortalTarget`. The outer job
decision cannot authorize an unknown series of model calls. Automated remote execution therefore
requires the runtime's network to remain behind the admitted Provider Gate; a black-box runtime
that cannot do so is ineligible. Transparent MITM, ambient proxying, and caller-supplied target
fields cannot establish this boundary.

#### Decision identity and local custody

The decision is explicit, never inferred consent, and binds opaque Principal identity plus Sigil
identity/revision digest—not either object—Run/occurrence/attempt/transmission generation, purpose,
exact target, canonical wire or exported-artifact digest, source
manifest and influence-label digests, safe residual-disclosure evidence digest, opaque restricted
lineage references, policy and disclosure-basis revisions, expiry, budgets, and allow/deny result. It contains no
caller-supplied full `ArtifactRef`, raw subject, filename, material-parent, source span, reversal
value, credential, or live Sigil/capability/grant/lease handle.

Within the trusted local Scout profile, its host-bound local subject and authentication generation
occupy the identity binding without claiming an enrolled Ward Principal or remote credential.
The public-text peer profile likewise binds its authenticated local initiator separately from
the enrolled workload/remote peer identities. Its explicit operator-operation binding is an
alternative to native Run binding, never a UUID placed in a Run/occurrence slot by convention.

`EgressDecision` is restricted, local-only, non-exportable, and non-bearer evidence. It never enters
the provider, peer, runtime, callback, log, Loom, or telemetry payload. The Gate passes only the
already sealed application bytes to transport; it neither appends decision metadata nor lets an
adapter serialize the verdict. A public projection uses only an opaque event id or the keyed
evidence form below.

Evidence can itself disclose private facts. A plain hash of a short prompt, filename, identifier,
or stable manifest can become a dictionary and linkage oracle, so canonical raw payload, source,
manifest, and content digests remain restricted local evidence. Exported, logged, or operator-wide
evidence instead uses a random opaque id or `EvidenceDigest@1`: a deployment-local,
domain-separated keyed digest scoped to consumer, purpose, record class, key epoch, and retention.
It receives no raw low-entropy metadata and makes no claim to anonymize its input.

#### Transmission and redelivery

Every actual transmission, including exact same-envelope redelivery, settles a fresh
`EgressDecision` before its first byte and atomically consumes the declared transmission/disclosure
budget. Transport redelivery under one road-owned attempt preserves the sealed bytes, target,
external/idempotency identity, road decision, and—when present—Cut/token namespace. Changed bytes,
target, actor, policy, custody route, semantic retry, resume with changed body, or fallback creates a
new road decision and, when transformation is required, a new Cut. Uncertain effects reconcile;
they never silently become a new semantic attempt.

#### Offline disclosure-accounting qualification

`closed-diagnostic-recording@1` is a local qualification profile for durable disclosure
admission and consumption. It accepts only the complete canonical bytes of the existing
`closed-diagnostic@1` candidate, under a separately host-pinned synthetic **export** binding.
The expected actor, Sigil digest, consumer, purpose and exact target cannot be taken from the
candidate's own Cut as their authority. This profile neither declares an enrolled A2A peer nor
admits a Portal, credential, network destination or arbitrary source material.

An acknowledged fresh database claim consumes one use and the complete candidate size against
stable host and purpose capacity and the individual Cut's disclosure ceiling. Host and purpose
identity are independent of Cut, attempt, transmission and Run identities; a new identifier,
renamed configuration or changed policy cannot reset retained capacity. Configuration changes
that disagree with retained ceilings refuse rather than minting a fresh account. No charge is
refunded after a claim, including refusal, expiry, cancellation or uncertain recording.

Only the trusted recording owner may turn its fresh claim into one process-local activation.
It consumes that activation before invoking its concrete bounded synchronous recorder, after
rechecking the host binding, Cut, expiry, current policy and exact Run effect fence. No await
separates the final check from the recorder handoff. The recorder receives exactly the candidate
bytes, without a decision envelope; no callback, caller-selected implementation, URL or filesystem
destination is admitted. Claim and completion shapes, copied objects and restored rows are not
live authority.

This profile linearizes admission before a local recorder call. A database Run lock does not
fence a later cancellation after commit, and no transaction spans an external effect. A future
transport owns its additional effect-time and complete-wire obligations: wrappers, authentication,
headers, polling and artifact requests cannot inherit this candidate's verification. Offline
recording is an acceptance witness for the accounting primitive, not evidence of A2A exchange,
remote disclosure safety, general anonymization or a normal application egress path.

#### Public-text peer network handoff

The Intercom profile requires its own typed network admission and custody. A closed diagnostic
recorder claim, Cut shape, Scout locator declaration or transport class grants it no authority.
Policy-independent pinned socket/TLS mechanisms may be reused under the mandatory Intercom gate;
Scout's source/locator policy is not peer trust.

The gate verifies the independently admitted public source and exact enrolled `A2ATarget`, then
seals the complete application request after authentication headers are prepared. Public protocol
wrappers, workload identifiers, nonce, path, poll parameters and TLS hostname have explicit
disclosure bases too. Every connect/TLS/application send checks current authority and consumes
its finite committed allowance in the same loop turn as the nonblocking syscall. TLS ciphertext
is bound to the complete sealed application value; the gate never claims to reconstruct it by
decrypting traffic. No private decision, source manifest, operator subject, credential or receipt
metadata may be appended to wire. No DNS or ambient proxy/redirect/retry road is opened.

Fresh physical signature wrappers over one retained semantic body require a new complete-wire
decision; they do not authorize repeating an unknown effect. Poll and cancellation requests have
their own exact source/target/purpose decision. Durable counters charge full declared application
bytes and conservative network allowance without refund; observed accepted network bytes are
reported separately. Failure to commit, verify current authority or reconcile an old attempt
cannot activate transport. This public-input profile does not authorize private Context, a
general anonymizer, voice offload or a new provider/peer fallback.

The [native public peer station](26-a2a.md#native-public-peer-station) adds an exact real
Run/station/source/target association. A process-owned live permit requires actual current
operator authentication and canonical ownership; retained admission, Sigil and checkpoint shapes
cannot construct it. Fresh authenticated reauthorization after restart cannot rearm a claimed or
closed semantic task. Run/claim fencing is checked at each physical handoff and before adoption
or resume. Trusted local cancellation may close adoption and retire local exchanges without
remote permission; remote poll/cancel still requires its own current exact authority and capacity.

#### Thresholds and refusal

Consent cannot repair missing lineage, override a prohibited category, or broaden named content and
destination. On the `0.0` public-safe to `1.0` strictly-private scale:

- below `portal_threshold`, raw egress remains eligible under destination, purpose, and category
  policy;
- at or above `portal_threshold`, a satisfying Privacy Cut is required; and
- at or above `forbidden_threshold`, raw egress is forbidden.

`portal_threshold` is the compatibility configuration name for the general remote-disclosure
threshold until a versioned policy schema replaces it. A target-specific rule may narrow that
baseline; peer trust, local ownership of a VPS, or containment of a coding runtime cannot widen it.

Non-declassifiable categories remain forbidden regardless of weight, and a failed, uncertain, or
expired Cut fails closed. Unknown recipient, retention, training, subprocessor, or custody facts
also refuse whenever policy depends on them. Current local-only source has no hostile-network
authorization and does not deliver this general egress gate; [State of
Work](../state-of-the-work.md#context-privatization-and-portal-egress) owns that boundary.

Several sanitized payloads can together reveal a stable identity or reconstruct withheld context.
Disclosure accounting must therefore cover related calls, retries, delegated child requests, and
intermediaries across one purpose. A future gate must enforce that cumulative policy before
transmission and keep enough bounded local evidence to detect reuse without exporting a
correlation identifier. Per-call censorship cannot guarantee anonymity. Resistance to semantic
re-identification needs adversarial evaluation against the stated observer and workload; neither
a general proof nor an implemented cumulative-disclosure gate is claimed here.

### Return Quarantine {#7-return-quarantine}

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
credential absence, Gate races, quarantine, and recovery. Coffin/Gate policy is Designed; no
hostile-runtime containment or Provider Gate implementation ships. Hostile browser safety and
effectful provider service likewise remain unclaimed according to [State of
Work](../state-of-the-work.md#delegated-agent-execution).

The general Egress Gate additionally needs allow/deny fixtures for every `RemoteTarget`; canonical
wire/export digest mismatch; target, model, peer, runtime, path, and custody-route substitution;
expired Cut/verifier/consent/policy; prohibited categories and unknown recipient facts; replay and
concurrent revocation; nested coding-agent child calls; first-byte enforcement; and proof that no
provider adapter, proxy, or A2A callback can bypass it.

Audit records correlate the admitted job/occurrence, profile, roots, policy and receipt revisions,
Gate decision, measured ceilings, terminal classification, and quarantine handoff. A provider
status message or fluent completion is attribution, not a host-observed effect receipt.

At minimum, privileged host intents, secret provisioning or binding failures, Shadow dispatches,
policy denials, Portal egress and Privacy Cut decisions, and compromise quarantine or revocation
emit structured security events. [Observability](29-observability.md) owns their record shape and
retention.

## Consequences

An unavailable boundary requires refusal, and policy shapes still need containment receipts before
they can support execution. Once delivered, local transformation and gated containment may make
lower-cost remote computation possible without handing the provider raw authority-bearing
context. Economic advantage cannot relax the boundary or justify widening an execution profile.