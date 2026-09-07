---
title: Portal Roads
icon: material/sign-direction
---

# :material-sign-direction: Portal Roads

> _A cheap road may still cross the wrong kingdom. Name the custodian before counting the toll._

An unattended indexing job is ready to send a document. Who may receive those bytes, and whose
account authorizes the work? Choose [labor ownership](../extensions/weaver/execution-roads.md)
first; then choose the service road and retain the evidence that could make it eligible.

This is operating design. [Portal declarations](portal.md) and probes exist, but general execution
is closed: every Portal grant remains quarantined while Privacy Cut and trusted Egress Gate are
absent. [Current maturity](../../state-of-the-work.md#context-privatization-and-portal-egress)
owns that delivery boundary.

## The default road

For unattended work, Reach/public services, CI and A2A-backed applications, prefer one direct
server API using a workload-issued API key, service account or workload identity. The initial
profile calls one upstream directly. This conditional preference establishes neither an admitted
profile nor a price winner. Every intermediary adds custody of request bytes, metadata,
credentials and receipts, plus an availability dependency.

Identify what the offered credential actually buys:

| Road | Account, custody and eligibility |
|---|---|
| BYOK policy gateway | Gateway credential plus separately scoped upstream key; the gateway receives admitted traffic. DLP, accounting, region or control-plane needs may justify study. It remains a Lab candidate until a delivered Gate/adapter binds the complete custody route. |
| Metered aggregator | Aggregator key and billing; it brokers or selects upstreams. An explicit catalogue, measured fallback or low-volume study may justify consideration, subject to the same unimplemented multi-hop boundary. Opaque cheapest routing and silent policy changes are excluded. |
| Human operator seat | Provider-supported interactive local Codex, Claude Code, Copilot, Antigravity or similar client holds OAuth/session, including supported automation surfaces. Useful for local coding outside Spellweaver automation; never a Portal or Reach/public-service credential or server-use grant. |
| Subscription bridge | Stores, translates, pools or reissues consumer OAuth/session behind another API key, often for quotas or cross-client use. Admission requires written upstream authorization for this exact server use and separate security review. |
| Local inference | No remote credential or provider custody. Local sensitive preprocessing, retrieval, routing and bulk work belong to a [Soulstone](soulstone/index.md), outside Portal. |

[Disclosure law](../../adr/09-security.md#portal-privatization-and-egress) requires an immutable,
ordered custody-route digest binding gateway endpoint and policy revision, ultimate
provider/model/region, redirects and every material hop. No delivered Gate schema, gateway
adapter, independent route evidence or selection receipt implements it. Gateway upstream/model
labels remain assertions without independent evidence; configuration and response labels cannot
substitute for proof. Anonymization changes eligible payload, never server licence,
account-pooling authorization or intermediary custody.

## Selection receipt

Retain a dated, source-linked packet covering every item below before considering the road
eligible. Use [Tithe/Toll](../extensions/toll.md) for quotas and money.

- Actual upstream/service, legal account owner, permitted usage class and provider-terms revision.
- Authentication kind, credential custodian and rotation, and any human session.
- Canonical endpoint, protocol, model identifier or revision, capabilities, region and every intermediary.
- Training, retention, abuse monitoring, deletion, subprocessors and zero-data-retention facts.
- Price units, gateway fees, included quota, rate and concurrency ceilings, expiry and hard spend cap.
- Permitted input classes and purposes, required Cut evidence and forbidden data.
- Explicit fallback set or none, with policy and cost for every member.
- Timeout, cancellation, idempotency, provider-job lookup, uncertain-effect reconciliation and return quarantine.
- Observation date and revalidation triggers for prices, terms, models, custody and ownership.

`free`, `included`, an operator-owned VPS or a successful smoke probe proves none of server-use
permission, caller identity, confidentiality, stable price or production availability. Recheck
terms, prices, retention and inventory before purchase or Bind. The dated candidate list later
supports comparison, not endorsement.

## One admitted remote attempt

The sequence below is the durable profile required by Reach and by asynchronous, paid,
autonomously retriable, or post-submit-reconcilable work. A strictly bounded immediate Portal call
may remain under its live `ModelGrant` or `CallGrant`; it still needs a committed road decision,
fresh byte-time `EgressDecision`, budgets, dispatch/security events, quarantine, and no silent
fallback, but it does not invent a `ServiceJobAttempt` merely to represent an immediate return.

```text
typed demand
→ local classification and bounded Context
→ Privacy Cut when required
→ exact provider, model, endpoint, purpose, and spend candidate
→ fresh payload-bound EgressDecision
→ reserve Tithe/Toll ceilings and persist one ServiceJobAttempt identity
→ commit SUBMITTING with idempotency and reconciliation identity
→ one credential-scoped Portal adapter
→ remote response quarantine and validation
→ known terminal receipt or INDETERMINATE plus provider lookup
→ reconcile usage, cost, custody, and terminal state
```

A semantic retry, redirect, fallback, model substitution, gateway route change, or different
destination is a new LychD-owned attempt with its own persisted identity and decision before any
bytes leave. Exact transport redelivery may retain one attempt only when the adapter contract
proves atomic server-side same-key/same-payload replay under the same sealed bytes, target, and
external/idempotency identity—or proves no prior effect; every physical send still needs a fresh
EgressDecision and bounded disclosure use. Crash
or timeout after `SUBMITTING` otherwise performs lookup by that identity and remains
`INDETERMINATE` when the provider cannot establish the effect; it never blindly resubmits.
Disable gateway-internal
automatic fallback, load balancing, and account/provider pooling; each eligible fallback member is
a separate pinned attempt. An unplanned internal switch is an integrity fault with an indeterminate
receipt, not successful resilience.

A gateway's marketing name is not the producing provider. Label provider, model, region,
retention, and training fields `gateway_asserted` unless independent signed or contractual evidence
establishes them. TLS authenticates the gateway endpoint, not whatever it selected behind itself.
When any of those facts is material to policy, require a direct provider road or separately
verifiable routing evidence. If a route cannot disclose or constrain that chain, it cannot carry
material whose policy depends on it.

## Reach placement

The [Reach deployment matrix](../../compositions/reach/deployments/index.md) changes where the
server Portal credential lives, never what authorizes it:

- `reach.home.public@1` keeps the provider gate and credentials in the separated home service;
- `reach.edge-home.public@1` keeps them at home—the VPS Discord edge receives none; and
- `reach.vps.public@1` gives one isolated VPS egress adapter only its exact provider/peer
  credential and destinations.

For every profile, a human coding subscription remains outside the bot. The practical starting
road is one direct server API, one low-cost model, one hard budget, no fallback, and a public
corpus-only E2E. Add another model or remote A2A only after the first route's custody, receipts,
quality, and cost are measured. A gateway or aggregator additionally waits for the multi-hop
target binding, independent route evidence, and receipt described above to be delivered.

## Candidate register — 2026-08-11

This register explains the current recommendation. Recheck the linked primary source before
spending or sending data.

| Candidate | Road | Current use in LychD | Position |
| --- | --- | --- | --- |
| Direct OpenAI, Anthropic, Google, or other upstream API | direct server API | intended production road for an exact eligible workload | Preferred; use provider-issued server credentials and pin the real model/destination |
| [DeepInfra](https://deepinfra.com/pricing), [Groq](https://groq.com/pricing), [Together](https://www.together.ai/pricing), or [Fireworks](https://fireworks.ai/pricing) | direct model-hosting API | no first-party LychD profile | Comparison pool only: benchmark the exact model, custody route, terms, limits, and dated price; no provider is a current winner |
| [OpenRouter](https://openrouter.ai/docs/faq) | metered aggregator and optional BYOK | built-in provider alias exists; dispatch remains quarantined | Useful catalogue; pin one `provider/model` candidate per LychD attempt, disable shared/internal fallback, and treat returned upstream identity as gateway-asserted |
| [Cloudflare AI Gateway](https://developers.cloudflare.com/ai-gateway/), [Vercel AI Gateway](https://vercel.com/docs/ai-gateway/), [Pydantic AI Gateway](https://pydantic.dev/docs/ai/overview/gateway/) | BYOK and/or managed gateway | no first-party LychD profile | Candidates when their policy, observability, region, or budget control justifies another custodian |
| [OpenCode Go](https://opencode.ai/docs/go/) | limited coding subscription with documented API endpoints | no admitted profile | Attractive operator experiment; unattended or third-party use waits for terms that unambiguously permit it |
| ChatGPT/Codex, Claude, Google AI, GitHub Copilot, and similar human plans | operator seat | external local coding runtime only | Keep their OAuth/session on the operator's machine and outside Reach, Portal adapters, and public A2A |
| [OmniRoute](https://github.com/diegosouzapw/OmniRoute) | self-hosted multi-provider gateway, free-tier router, and optional subscription/API bridge | upstream reference candidate; no admitted profile | Study its catalogue, cost telemetry, circuit breakers, and routing; refuse `auto`/silent fallback, quota pooling, remote OAuth, MITM, memory, and public exposure for any LychD trial |
| [openusage](https://github.com/janekbaraniewski/openusage) | local usage dashboard | reference candidate only | Prefer the read-only telemetry pattern; a dashboard observes quota and cost but grants no routing authority |
| [AIUsage](https://github.com/sylearn/AIUsage), [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI), and its dashboards | dashboard plus optional subscription/API proxy | Lab references only | Separate harmless local observation from credential switching, translation, LAN exposure, or subscription pooling; none is an admitted Portal |
| [Sub2API](https://github.com/Wei-Shaw/sub2api) | subscription-to-API gateway and account pool | rejected production candidate | Its own project warns of upstream Terms-of-Service risk; do not use it to serve Reach or third parties |

The first implementation target is direct-only: one exact server API, provider, endpoint, region,
model revision, credential, data policy, hard budget, and no fallback, selected only after its
maintained receipt closes every field above. No commercial candidate has completed that selection
gate yet. Price or reputation alone does not nominate a first profile; every comparison and
quality-escalation candidate remains non-canonical until an exact dated receipt exists.

Cloudflare, Pydantic, Vercel, and OpenRouter remain unresolved multi-hop comparisons. They may be
benchmarked for DLP, accounting, OpenTelemetry, catalogue reach, or cost without being stacked or
promoted. OmniRoute is the named gateway/dashboard candidate; `openusage` and AIUsage are close
dashboard comparisons; CLIProxyAPI is a proxy engine AIUsage can manage; Sub2API is a full
subscription-quota gateway. Their similar surfaces conceal different authority and risk.
Read-only usage collection is a different road from moving OAuth credentials and model traffic
through a new service.

An OmniRoute or CLIProxyAPI Lab trial must pin a reviewed revision, bind loopback only, add an
independent firewall, require non-default management and client API authentication, and use only
synthetic public fixtures plus one disposable, trial-scoped API key. Run an ephemeral profile with
no subscription/account credential, persistent volume, raw prompt/response log, semantic or prompt
cache, cloud sync, backup, credential import, or retained credential store. Disable remote/LAN
management, browser cookies, subscription OAuth, account/quota pooling, provider fingerprint
impersonation, stealth/obfuscation, transparent MITM, `auto`/Fusion/pipeline routing, memory, and
remote mode. Destroy the profile and revoke the key after the trial. Those features change legal
basis, destination, payload, or credential custody and cannot be repaired by calling the gateway
local. No such trial is a Reach or production Portal profile.

## Economical fan-out

Parallelism belongs to an exact versioned Workflow/Pattern policy above the road, not Dispatcher
and not an opaque provider switch. Dispatcher binds an eligible ready capability; it does not judge
quality or price. The Pattern may:

1. perform retrieval, deterministic redaction, classification, caching eligibility, and cheap
   routing locally;
2. use one primary worker for ordinary work;
3. add two to four heterogeneous low-cost reviewers only when diversity can change the decision;
4. invoke one stronger critic on disagreement, failed validation, or high consequence; and
5. stop on the admitted request, token, concurrency, time, and spend ceilings.

Do not run all-to-all review or many identical frontier branches by default. Cache only material
whose classification and audience allow that exact reuse. A node hop carries an admitted typed
task and evidence bundle; it never carries a reusable human subscription token, ambient Sigil, or
raw private Context.
