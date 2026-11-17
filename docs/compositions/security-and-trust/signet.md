---
title: Signet
icon: material/seal-variant
---

# Signet

An operator offers spare compute for private work. Before sending a request, a client needs to
know which program will receive it, who can read it, and whether the required protections are
active. **Signet** qualifies that execution environment and keeps signed evidence for individual
requests. Its seal names the conditions it checked and the protections the client may rely on.

Signet is a Native Reference Composition. Its identity is `signet.qualification`, revision `1`.
Its Pattern `signet.qualify_node@1` takes an authorized request naming the node, workload,
execution profile, adversary and required claims. It returns a qualification recording which
claims the evidence supports, which failed and which remain unobserved. A certificate identifies those gaps and attests
only to the claims the evidence supports. [State of Work](../../state-of-the-work.md#composition-portfolio-delivery)
records the implementation status of the collector, issuer and protected request path.

## Qualification has its own lifecycle

The lasting record is a qualification of an exact node, workload and policy generation. It keeps
the authorized inspection, evidence, supported and missing claims, issued assessments and the
conditions that invalidate them. A renewed qualification preserves the earlier finding and its
consumers; it does not rewrite history after configuration or trust references change.

This application owns the qualification question and its disposition, recipient-specific signed
results, expiry/revocation, dependent consumer notices, and retest obligations. An interrupted
inspection keeps its incomplete evidence and any unsettled test effects. A refused or partial
qualification can produce a useful report without making the node eligible for private work.

[Thorn](thorn/index.md) separately owns security operations: incident defense, investigation,
response and corrections. A settled finding or repair retest can inform a qualification, while
qualification failure can inform an independently admitted security case. Neither application
owns the other's judgment. Typed collectors, platform verifiers and host actuators supply
mechanisms under their existing architectural owners.

## What the certificate guarantees

A certificate qualifies an exact execution profile against a declared adversary. It states which
claims passed, the evidence and assumptions supporting them, when they expire, and what changes
invalidate them. The client selects acceptable profiles and issuers independently of the provider.
Publishing or signing a claim does not make an unsupported claim true.

Certificates, authenticated stamps and client presentation preserve the claim class and exact
profile requirements. A valid inspection stamp cannot satisfy a protected-processing requirement;
unsupported claims remain missing rather than collapsing into a generic “Signet verified” result.

An inspection profile can state: **“The listed checks found no prohibited collection in the
observed configuration and exercises.”** It must retain missing coverage. A protected-execution
profile additionally requires mechanisms that prevent the excluded administrator from reading
request contents or changing their handling within the qualified boundary. Successful scanning
alone cannot qualify that stronger claim.

A protected-processing certificate states that **“This approved workload handles request contents
only for the admitted task, under the profile's enforced access, output and retention rules.”**
Its scope includes the components and request interval actually qualified. It depends on the
approved code, enforcement and named hardware/firmware roots; it is not an unconditional proof
against every physical attack, implementation defect or unknown side channel. A formal proof
under a bounded model would retain those assumptions too.

Signet qualifies processing confidentiality. It does not anonymize a prompt, hide the research
question it expresses, conceal an account or IP address, prove model quality, or authorize the
disclosure. The [anonymization contract](../../sepulcher/aspects/weaver/anonymization.md)
owns those content and cumulative-disclosure assessments. Stamps must not label a request
“anonymous” merely because it used a qualified node.

## Conditions for a qualified host

Signet targets LychD's supported Linux host environment. Participation is open to
any operator who can satisfy an admitted profile. Installing the Composition does not make every
Linux machine or GPU eligible for the same guarantee. A dedicated commercial node may simplify
qualification; a suitable isolated execution environment can also separate private inference
from other work. An ordinary container does not by itself exclude its host administrator.

For the stronger protected-processing profile, the operator accepts these conditions:

| Condition | Required evidence or enforcement |
| --- | --- |
| Reviewed Linux/FOSS stack | Pin source/build provenance, actual executable artifacts, kernel configuration, collector, inference runtime, model assets and policy. Version strings alone are insufficient. Name firmware, device components and other trusted dependencies outside that source closure. |
| Trustworthy launch and observations | Establish how the client knows the measured stack is the one serving its session, and which lower-layer roots protect those measurements from the excluded operator. |
| Restricted administration | Prevent the excluded operator from reading inference memory, attaching debuggers or tracers, enabling content dumps/logging, or substituting admitted code/configuration. An operator may retain unrelated infrastructure control only where the execution boundary excludes it. |
| Approved handling of plaintext | Qualify the complete data path, permitted outputs, storage, caches, crash handling and onward calls. A logger inside an approved process is still a logger. |
| Protected evidence and connection keys | Keep signing and decryption keys inaccessible to the excluded operator, bound to the approved environment and usable only through its admitted protocol. No arbitrary message-signing interface may mint successful stamps. |
| Continuous operation | Keep the required enforcement and observation components active at accepted revisions, with bounded evidence age and explicit treatment of lost coverage. |
| Controlled change and recovery | Reappraise affected claims after updates, reboot, migration or configuration drift. Qualify prevention or detection of snapshot, cloning and rollback; retain withdrawal, interruption, cleanup and retest obligations. |
| Inspectable qualification | Publish the profile's required safe transparency view and let clients verify its relationship to the certificate and approved references. |

FOSS makes the reviewed design inspectable. Reproducible builds can connect source to an artifact;
independent measurements must still connect that artifact to the running recipient. A profile
cannot silently treat closed firmware or an unmeasured device as covered by a claim about its
Linux source. If a required dependency or enforcement mechanism is unsupported, Signet reports
the gap and withholds the dependent guarantee.

The restrictions are technical admission conditions, not a promise to avoid using available
root privileges. On an otherwise unchanged FOSS system, a permitted debugger can read inference
memory and detach without changing the kernel version. The certified mode must prevent that
access under its declared trust model. The inspector's own high privilege remains confined to
the [typed collector boundary](#privileged-inspection-and-host-control).

## What high privilege can and cannot establish

For an ordinary service, elevated inspection can examine logging, tracing, process access,
debuggers, dumps, caches, swap, snapshots, backups and network destinations. It can find a known
misconfiguration or observe a synthetic request reaching an unwanted sink. Its conclusion names
the actual checks, visibility and time; denied access is a gap, not a clean result.

Against a host that controls the scanner's observations, more privilege does not supply an
independent witness. Consider two executions: one runs a clean inference guest; the other presents
that same guest view while an outer hypervisor copies its memory. A scanner confined to that
view can receive the same readings in both. If it accepts the first execution, those observations
alone cannot justify rejecting the second. This is an observation-limit argument under the
stated hostile substrate, not a claim that every confidential-computing construction is impossible.

Random canaries, continuous scanning and higher in-guest privilege do not remove that limit. A
logger may sit outside the observed layer or activate after inspection. No current snapshot can
establish that input was never copied previously or will never be copied later.

| Required claim | What could support it | Remaining dependency |
| --- | --- | --- |
| Specified collection paths were not observed | Authorized configuration checks and synthetic exercises | Cooperative observation substrate, coverage and freshness |
| An approved launch was measured | Independently rooted measurements and reference appraisal | Which components were measured and what can change afterward |
| A named administrator cannot inspect this session's plaintext | A qualified execution boundary excluding that administrator, approved application and protected connection | Hardware/firmware roots, workload/configuration, device path and declared threat exclusions |
| The node never spies under any circumstances | Outside the scope of every Signet certificate | Historical capture, arbitrary lower-layer compromise and future behaviour exceed the claim |

## From inspection to protected execution

A controlled appliance can boot a reviewed,
restricted image and remove interactive administrator access while the workload runs, provided
the client has an independent basis for trusting that launch and its hardware. A hardware-backed
confidential workload can instead isolate the approved software from a participating host's
administrator or hypervisor under its specific platform threat model. Giving an inspector root
inside an ordinary VM is neither construction.

Measured boot does not itself provide memory confidentiality, and an immutable image still needs
controls for mutable configuration, privileged access and request handling. The approved inference
application may intentionally log or export data even inside protected execution. Its actual code,
policy, administration, update mechanism and outbound paths therefore belong in the qualification.
That closure includes model/tokenizer assets, adapters, templates, dynamically loaded code and
mutable configuration that affect handling. The profile must establish how they remain approved
through execution; an attested boot or container digest alone does not cover later-loaded material.
If the client distrusts the service operator, it must approve that guest/application or trust an
approver outside the operator's control. The operator cannot retain qualification while freely
changing that software, its logging configuration or privileged guest access. A confidential VM
running the operator's admitted logger would protect the wrong thing.

Follow the complete plaintext path: endpoint and TLS termination, preprocessing/tokenization,
CPU memory, model runtime, driver, GPU memory and device links, KV/prefix caches, output, errors,
retry and onward providers. Evidence for a GPU or public ingress endpoint alone cannot qualify
the task. Different valid CPU/GPU reports need a proved association and the required protected
communication path. Side channels, physical access, client identity, traffic metadata and
availability retain explicit scope and exclusions.

NVIDIA's [Confidential Bare Metal threat model](https://docs.nvidia.com/confidential-computing/bare-metal/threat-model)
trusts the model owner's privileged software and administrators and does not isolate end-user
data from them. Other deployment modalities have different boundaries; the exact platform and
application profile must be qualified rather than inferred from a product family or the phrase
“confidential computing.” Consumer-GPU compatibility and performance require evidence for the exact platform.
The separate [VM threat model](https://docs.nvidia.com/confidential-computing/virtual-machines/threat-model)
protects against specified infrastructure attackers while retaining guest software and
administrators in its trusted boundary. Its [supported-platform matrix](https://docs.nvidia.com/confidential-computing/virtual-machines/supported-platforms)
must be checked for the exact CPU, GPU, firmware, driver and interconnect mode; neither all RTX
hardware nor all multi-GPU arrangements have the same support or protection.

Apple's [Private Cloud Compute design](https://security.apple.com/blog/private-cloud-compute/)
describes a stronger construction around restricted runtime access, attestation and published
software. Its [June 2026 expansion](https://security.apple.com/blog/expanding-pcc/) describes a
third-party CPU/GPU confidential-computing path with additional controls. These are first-party
design accounts, not an independent audit or a transferable guarantee for a LychD node. They
show why the stronger direction concerns the complete execution service, not a scanner binary.

## Qualification records and public evidence

A qualification or certificate binds issuer and method, node/workload and policy/profile
revisions, threat model, supported/failed/unobserved claims, safe evidence references, collection
time and uncertainty, expiry and revocation/supersession information. Necessary software,
configuration and platform-security measurements are part of its restricted evidence closure.
Public or recipient-specific derivatives disclose only admitted identifiers and claims; raw
configuration, private digests and captures remain under custody policy.

The qualification names the trusted verifier, workload approver, collector, reference/policy
providers and their permitted roles. Their compromise can invalidate the claims they support;
an independently selected issuer and a genuine signature do not eliminate that trust dependency.

The required public snapshot is a versioned, sanitized view of that qualification: accepted
software/build references, relevant configuration and enforcement claims, collection method and
coverage, observed generation, omissions, validity and withdrawal status. It binds back to the
certificate and retained restricted evidence so a reviewer can examine how a published conclusion
was reached. Claims with hidden supporting details remain explicitly dependent on the admitted
verifier; a redacted snapshot cannot pretend to make every observation publicly reproducible.

Publication excludes prompts, responses, memory captures, credentials, unrelated host files and
other tenants' information. Predictable plaintext hashes can reveal private inputs too; use opaque
references or Security's scoped evidence digests where correlation is needed. Public software
digests have a different purpose. The snapshot's provenance and signature still need a trustworthy
collector and protected key. A host publishing its own invented clean state gains no stronger
qualification. Relevant changes supersede the current view while preserving historical findings.

A signed assessment is non-bearer evidence. The relying client chooses trusted issuers and required
claims; it does not acquire those requirements from the node's self-description. The runtime
gate enforces current acceptance independently of this application's availability. Qualification
does not enroll a peer, grant privilege, authorize a task or declassify Context.

## A request from admission to final stamp

The node certificate establishes eligibility for its named profile. Each request needs current
admission evidence before disclosure and a separate completion record afterward. These stamps
answer different questions; a successful final receipt cannot retroactively protect an input
sent to an unqualified destination.

For a request requiring protection against a hostile administrator, the client, verifier and
protected workload share the following admission procedure.

1. The client supplies a fresh challenge, opaque request identity and required execution-profile
   identifiers, without revealing private task contents or its local protected-fact policy.
2. The approved protected workload creates and retains its private connection and request-stamp
   keys inside the qualified boundary. Evidence binds both public keys, challenge,
   workload/configuration, execution lineage/epoch and required platform state. These runtime keys
   have distinct roles from the qualification issuer's certificate-signing key.
3. A verifier appraises endorsements, reference values, security versions, device association,
   policy, freshness and revocation. The client checks the result under its own admission policy.
4. The client prepares the exact encrypted application envelope locally using the qualified
   protocol and sends only its nonrevealing ciphertext commitment on the admission control path.
   This exchange has its own disclosure basis; raw inputs and their predictable hashes stay local.
5. The approved protected producer signs an admission stamp with the bound request-stamp key.
   It binds the accepted appraisal, challenge, request identity, session/keys, workload/model and
   policy revisions, validity, and that commitment under still-current controls.
6. The client verifies the stamp and possession of the bound connection key, then Security's gate
   releases only the matching envelope. The receiver checks its commitment, requester/session
   binding and current controls, then atomically consumes that admission occurrence before
   processing. The confidential application channel terminates inside the protected boundary,
   not at an outside proxy.

The receiver enforces its restrictions while the sender's Security gate retains disclosure
authority. Another request, onward recipient, retry or fallback needs its own admission; an
uncertain occurrence is reconciled before any repetition.

### Replay, forks and continuity

Matching bytes and signatures do not prevent replay of the same request under the same session.
The receiver retains the occurrence's immutable commitment and in-flight/terminal disposition.
A duplicate can obtain only an admitted status or a separately permitted retained result for
that occurrence; it cannot start another execution. Claim and settlement must survive supported
recovery without conflicting final stamps. This is at-most-once admission within the qualified scope, not a promise of
exactly-once execution or a completed result after a crash.

A consumed flag inside a restorable guest is insufficient. A snapshot or clone can retain the
keys and challenge while rolling back the consumption ledger and monitor history. The profile
must prevent those operations through independently enforced platform controls or qualify a
continuity mechanism outside the rollbackable state. Admissions and finals bind the accepted
execution lineage/epoch; abandoned branches must lose authority to process or certify work.
Reattestation alone cannot fence a clone retaining already released keys. If the platform cannot
establish the required continuity, Signet withholds the dependent replay, monitoring and retention
claims. A clean final stamp from one branch cannot certify cleanup in every hidden branch.

### Freshness and loss of contact

The persistent collector and enforcement components are deterministic trusted mechanisms; a model
may interpret their evidence without becoming their measurement or access-control authority.
The required trusted monitor remains active during processing at the accepted revision. It records
bounded observations of control state and relevant changes; a fresh heartbeat alone does not
establish uninterrupted protection. Enforcement must prevent forbidden access between checks,
including inside the inference process. Event loss, monitor interruption, changed configuration,
restart, migration or revoked references suspend affected eligibility and force reappraisal.
The request policy defines protected abort, cleanup and reconciliation for already admitted work.

The profile identifies the trusted basis for time or epochs, the maximum age of observations,
appraisals and revocation status, the maximum offline interval, and the detection/stop bounds.
The excluded host's wall clock cannot establish those bounds. A fresh signature over old
measurements is not fresh state. The sender and receiver enforce the admitted limits at their
respective release and processing boundaries; a paused/resumed instance or an old connection
cannot silently renew them. No profile may assume instantaneous knowledge of a remote revocation.

When an enforcing gate learns of withdrawal or cannot establish required validity within those
bounds, it refuses further dependent admission and release. An outage permits only the explicitly
bounded, still-valid lease, never an indefinite extension of the last good assessment. In-flight
processing, result delivery and cleanup follow the predeclared protected stopping policy; isolation
continues while private data remains. Expiry and revocation cannot recall input already delivered.
A vendor-signed update is not automatically an accepted reference version or application revision.

### What the final stamp can establish

At completion, the protected producer signs a final stamp referring to the same admission,
request and session. It binds the result envelope, actual workload/policy generation, processing
interval and time uncertainty, observations and coverage gaps, applicable control events, terminal
outcome, execution lineage/epoch, and evidence for required cleanup. Streaming responses need
sequence/transcript binding; an early chunk cannot stand in for successful completion. The stamp
is restricted evidence unless its release has a separate disclosure basis.

The producer derives that record from the protected occurrence: admitted input commitment,
dispatch, actual workload/model and custody path, result bytes and control/cleanup evidence.
It must not sign a host-supplied response digest or success assertion merely because the fields
match. An admitted onward computation needs a qualified evidence chain back to this occurrence;
otherwise the producer cannot certify that it performed the work. The client checks the final
signature, bindings, outcome and required evidence before accepting successful completion.
This still relies on the approved producer and execution boundary; it is not a cryptographic
proof that a model calculation was mathematically correct.

A successful stamp can state: **“Request R was processed by workload X under profile Y; the
required evidence for this interval was complete and its checks found no violation.”** Its
meaning inherits the certificate's enforced protections and assumptions. An inspection-only
stamp retains the weaker observation claim. Neither a signature nor a reported deletion proves
that an unobserved copy never existed.

Refusal, interruption and inconclusive evidence remain distinct from success. Missing final
evidence leaves completion unproven; the client must not invent a successful stamp, automatically
repeat the request or infer that no disclosure occurred. Later revocation can invalidate reliance
on a prior result without erasing its historical record.

[RFC 9334](https://www.rfc-editor.org/rfc/rfc9334.html#section-12.1) requires protection of the
attesting environment and key from the environment being measured. Its
[freshness discussion](https://www.rfc-editor.org/rfc/rfc9334.html#section-10) acknowledges that
state may change immediately after evidence generation. Before/after observations therefore
cannot replace runtime enforcement.

### Copied certificates and network interception

Certificates and safe public snapshots may be copied; they contain no session decryption secret.
A copied genuine report must not authorize another endpoint, key, request or session. In
certificate-authenticated [TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446.html#section-4.4.3),
authentication requires proof of the private key bound to that handshake; copying the public
certificate alone supplies neither that proof nor its traffic secrets. Signet additionally needs
the protected-key/workload binding above. Ordinary TLS authentication alone does not supply it.

The protected request path must not admit replayable early data. Session resumption does not
substitute for current qualification or occurrence authority. [TLS 1.3's anti-replay discussion](https://www.rfc-editor.org/rfc/rfc8446.html#section-8)
also leaves application retries to application-level defenses; encrypted transport does not
supply Signet's admission-consumption invariant.

An interceptor terminating the application channel outside the qualified boundary fails that
binding. Relaying encrypted traffic to a real protected workload may preserve content
confidentiality but cannot establish the relay's machine identity or physical location. Stolen
private keys, compromised trusted issuers and endpoint defects remain threats requiring their own
withdrawal and recovery; no stamp repairs data already exposed.

## Privileged inspection and host control

High-privilege inspection requires an operator-admitted host collector and an exact observation
or test profile. Under [Privilege](../../adr/10-privilege.md#decision-authority-before-effect),
the consumer accepts registered target/profile identifiers, enumerated observations, deadlines
and resource limits; the requesting model supplies no arbitrary shell, script, path or environment.
The host independently checks current authority. The scanner does not grant itself elevation or
give the general Vessel root access.

Passive reads, temporary instrumentation, synthetic crash/dump tests and a controlled boot or
configuration change have different effects. Each needs its own producer/consumer, scope, receipts,
restoration and stopping conditions. Qualification can request a supported preparation through
the existing effect owner; it cannot invent a generic host actuator. A malicious assessment
client is also a threat: privileged access must not expose the host's unrelated files, credentials,
other users or tenants to that client. Collectors and their output need containment and custody.

## First proof and defeat conditions

Begin with synthetic observation and transport fixtures. Fix the workload, adversary, collector,
reference values, criteria, observation/effect authority and budgets before comparison.

| Fixture | Required distinction |
| --- | --- |
| A clean guest and a memory-copying outer-host fixture expose the same scanner view | Scan-only evidence cannot certify protection from that outer host. |
| Prompt logging is off but a proxy, error trace, cache or synthetic dump retains a canary | Identify the exercised leak without certifying unobserved paths. |
| Access is denied or observations are incomplete | Preserve unknown coverage; do not emit the missing claim. |
| Approved measured software intentionally exports inputs | Launch integrity does not establish acceptable application handling. |
| An unchanged FOSS kernel permits an administrator to copy request memory | Source availability and version checks do not substitute for enforced access restrictions. |
| Wrong issuer, workload, policy, device association, challenge or expiry | Refuse the dependent session before plaintext release. |
| Genuine evidence is paired with an external key or unprotected channel terminator | Reject substitution; endpoint authentication does not supply key confinement. |
| A public snapshot disagrees with the retained evidence or current generation | Withhold the dependent claim; publication alone establishes no trustworthy measurement. |
| A snapshot exposes sensitive configuration, stable private identifiers or predictable input hashes | Refuse that publication; redaction must not conceal which claims remain dependent on hidden evidence. |
| A required monitor stops, loses events or misses its freshness bound | Suspend affected admission; retain coverage gaps and the existing request's protection/cleanup obligations. |
| A stamp is replayed for another request/session, or a final stamp names different result bytes | Reject the binding rather than accepting a familiar certificate. |
| The same valid admission and ciphertext arrive twice, concurrently or after completion | Only one occurrence is consumed; duplicates cannot start another execution or conflict in settlement. |
| A snapshot forks keys, consumed state or monitor history into two apparently valid instances | Enforce the qualified continuity/fencing mechanism or withhold the dependent claim; one branch's cleanup does not cover the other. |
| The host freezes its clock, delays revocation or blocks the verifier | Enforce declared freshness/offline bounds; do not treat the last good result as indefinitely current. |
| A host supplies a plausible result envelope or substitutes an unqualified worker | A matching shape and digest do not replace the protected input-to-execution-to-result evidence chain. |
| A genuine inspection stamp is offered for a protected-processing requirement | Preserve authenticated claim/profile semantics and refuse the downgrade. |
| A pinned image loads an unapproved model, adapter, template or executable after measurement | The full runtime closure fails qualification; launch evidence cannot cover the substitution. |
| A response arrives without final evidence, or cleanup cannot be established | Keep completion inconclusive; do not certify success or repeat an uncertain occurrence. |
| Configuration changes or required evidence is revoked | Invalidate affected current eligibility while retaining historical findings and consumer obligations. |
| Hostile collector output or a certificate requests root, another target or private source disclosure | No authority is acquired. |
| Cancellation interrupts temporary instrumentation or preparation | Retain accountable cleanup/restoration and unresolved effects. |

Fixture success qualifies only those checks. A cooperative-host profile needs a separately
authorized observed host occurrence; a hostile-operator profile needs one exact qualified platform
and protected workload. Synthetic quotes, a successful scan or isolated GPU evidence cannot
advance that claim. Changed collector, firmware, runtime, configuration or policy reopens the
affected qualification. Reports of limitations, refusal and inconclusive evidence are valid
outcomes; they cannot be presented as a usable protected session.

Portal carries sender-selected model inference; Intercom carries a sovereign peer task.
[Anonymization](../../sepulcher/aspects/weaver/anonymization.md#assess-the-remote-host-separately)
prepares and verifies the disclosure branch;
[Security](../../adr/09-security.md#inspection-and-destination-evidence) admits the exact release.
Destination qualification supplies evidence to that decision and cannot widen it.
