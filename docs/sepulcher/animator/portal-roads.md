---
title: Portal Roads
icon: material/sign-direction
---

# :material-sign-direction: Portal Roads

> _A cheap road may still cross the wrong kingdom. Name the custodian before counting the toll._

This page owns the operator's choice of remote model road. It does not make current prices,
provider claims, or a consumer subscription architectural truth. [Portal](portal.md) owns the
remote Animator binding, [Security](../../adr/09-security.md#portal-privatization-and-egress) owns
each exact egress decision, and [Tithe and Toll](../extensions/toll.md) own currency-neutral quotas
and monetary reservation/settlement respectively. Provider terms, prices, retention, and model
inventories must be observed again before purchase and before Bind.

[Spellweaver execution roads](../extensions/weaver/execution-roads.md) decides whether a station
needs native cognition, a sovereign peer task, or a delegated coding runtime before this page helps
select a model provider. Provider economics never choose that labor boundary.

!!! warning "The general Portal road is still closed"
    Portal declaration and observation exist, but Dispatcher quarantines every Portal grant. The
    Privacy Cut and trusted Portal Egress Gate do not ship. This selection guide is accepted
    operating doctrine and an implementation target, not evidence of remote execution. [State of
    Work](../../state-of-the-work.md#context-privatization-and-portal-egress) owns that boundary.

## The default road

For unattended work, a public Reach service, CI, or A2A-backed application, prefer one exact
server API credential issued for that workload. The first admitted profile calls its upstream
directly. Every extra hop becomes another custodian of request bytes, metadata, credentials,
receipts, and availability.

Accepted Security law now requires an immutable ordered custody-route digest binding gateway
endpoint and policy revision, ultimate provider/model/region, redirects, and every material hop.
No delivered Egress Gate schema, gateway adapter, independent route evidence, or selection receipt
implements that law. BYOK gateways and aggregators therefore remain Lab candidates; gateway
configuration or a response label cannot fill the missing executable proof.

Use human subscriptions only through their provider-supported interactive clients and automation
surfaces. A local coding-agent seat can be valuable without becoming a Portal. Anonymization
changes the eligible payload; it does not convert a human seat into a server licence, authorize
account pooling, or erase an intermediary's custody.

| Road | Credential and custody | Fitting use | Canonical stance |
| --- | --- | --- | --- |
| **Direct server API** | workload API key, service account, or workload identity; one upstream | Reach, A2A, CI, unattended agents | **Preferred baseline** when the exact provider and policy are eligible |
| **BYOK policy gateway** | gateway credential plus separately scoped upstream key; gateway sees admitted traffic | DLP, accounting, regional routing, or one control plane | Lab until a delivered Gate/adapter binds the complete custody route; upstream/model claims remain gateway assertions without independent evidence |
| **Metered aggregator** | aggregator key and billing relationship; aggregator selects or brokers upstream capacity | explicit model catalogue, measured fallback, low-volume experiments | Lab under the same undelivered multi-hop profile; no opaque cheapest-route or silent policy change |
| **Operator seat** | human OAuth/session held by the supported local client | interactive Codex, Claude Code, Copilot, Antigravity, or another coding tool | Outside Spellweaver automation; not a Portal and never the Reach/public-service credential |
| **Subscription bridge** | consumer OAuth/session is stored, translated, pooled, or re-issued behind another API key | quota pooling or cross-client use | **Not admitted** without written upstream authorization for that exact server use and a separate security review |
| **Local inference** | no remote credential or provider custody | sensitive preprocessing, retrieval, routing, bulk work | A [Soulstone](soulstone/index.md), not a Portal |

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

## Selection receipt

Before an operator promotes a candidate road, retain a dated, source-linked decision packet with:

- upstream service, legal account owner, permitted usage class, and the provider terms revision;
- authentication kind, credential custodian, rotation path, and whether a human session is
  involved;
- canonical endpoint, protocol, model id or revision, capabilities, region, and every intermediary;
- training, retention, abuse-monitoring, deletion, subprocessors, and zero-data-retention facts;
- price units, gateway fees, included quota, rate/concurrency ceilings, expiry, and a hard spend cap;
- input classes and purposes allowed through the road, required Cut evidence, and forbidden data;
- explicit fallback set—or no fallback—with the policy and cost of every member;
- timeout, cancellation, idempotency, provider-job lookup, uncertain-effect reconciliation, and
  returned-material quarantine; and
- the observed date and revalidation trigger for price, terms, models, custody, or ownership.

The packet is evidence for a decision, not a timeless endorsement. `free`, `included`, a VPS under
operator control, or a successful smoke request proves none of server-use permission, caller
identity, confidentiality, stable price, or production availability.

## Candidate register — 2026-08-11

This register explains the current recommendation. Recheck the linked primary source before
spending or sending data.

| Candidate | Road | Current use in LychD | Position |
| --- | --- | --- | --- |
| Direct OpenAI, Anthropic, Google, or other upstream API | direct server API | intended production road for an exact eligible workload | Preferred; use provider-issued server credentials and pin the real model/destination |
| [DeepInfra](https://deepinfra.com/pricing), [Groq](https://groq.com/pricing), [Together](https://www.together.ai/pricing), or [Fireworks](https://fireworks.ai/pricing) | direct model-hosting API | no first-party LychD profile | Benchmark exact model and custody profiles; DeepInfra is the current low-cost primary-worker candidate, not a permanent winner |
| [OpenRouter](https://openrouter.ai/docs/faq) | metered aggregator and optional BYOK | built-in provider alias exists; dispatch remains quarantined | Useful catalogue; pin one `provider/model` candidate per LychD attempt, disable shared/internal fallback, and treat returned upstream identity as gateway-asserted |
| [Cloudflare AI Gateway](https://developers.cloudflare.com/ai-gateway/), [Vercel AI Gateway](https://vercel.com/docs/ai-gateway/), [Pydantic AI Gateway](https://pydantic.dev/docs/ai/overview/gateway/) | BYOK and/or managed gateway | no first-party LychD profile | Candidates when their policy, observability, region, or budget control justifies another custodian |
| [OpenCode Go](https://opencode.ai/docs/go/) | limited coding subscription with documented API endpoints | no admitted profile | Attractive operator experiment; unattended or third-party use waits for terms that unambiguously permit it |
| ChatGPT/Codex, Claude, Google AI, GitHub Copilot, and similar human plans | operator seat | external local coding runtime only | Keep their OAuth/session on the operator's machine and outside Reach, Portal adapters, and public A2A |
| [OmniRoute](https://github.com/diegosouzapw/OmniRoute) | self-hosted multi-provider gateway, free-tier router, and optional subscription/API bridge | upstream reference candidate; no admitted profile | Study its catalogue, cost telemetry, circuit breakers, and routing; refuse `auto`/silent fallback, quota pooling, remote OAuth, MITM, memory, and public exposure for any LychD trial |
| [openusage](https://github.com/janekbaraniewski/openusage) | local usage dashboard | reference candidate only | Prefer the read-only telemetry pattern; a dashboard observes quota and cost but grants no routing authority |
| [AIUsage](https://github.com/sylearn/AIUsage), [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI), and its dashboards | dashboard plus optional subscription/API proxy | Lab references only | Separate harmless local observation from credential switching, translation, LAN exposure, or subscription pooling; none is an admitted Portal |
| [Sub2API](https://github.com/Wei-Shaw/sub2api) | subscription-to-API gateway and account pool | rejected production candidate | Its own project warns of upstream Terms-of-Service risk; do not use it to serve Reach or third parties |
| [Hyvemind](https://github.com/Unravl/Hyvemind) | local multi-model agent orchestrator | upstream reference candidate only | Useful bounded fan-out, circuit-breaker, cache, and reviewer pattern; not itself a trusted provider or subscription entitlement |

The first implementation target is direct-only: one exact server API, provider, endpoint, region,
model revision, credential, data policy, hard budget, and no fallback, selected only after its
maintained receipt closes every field above. No commercial candidate has completed that selection
gate yet. Current price research makes a low-cost DeepInfra model the first comparison candidate
and direct OpenAI API the first quality-escalation candidate, but neither is a canonical profile
until the exact receipt exists.

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
3. add two to four heterogeneous low-cost Scouts only when diversity can change the decision;
4. invoke one stronger critic on disagreement, failed validation, or high consequence; and
5. stop on the admitted request, token, concurrency, time, and spend ceilings.

Do not run all-to-all review or many identical frontier branches by default. Cache only material
whose classification and audience allow that exact reuse. A node hop carries an admitted typed
task and evidence bundle; it never carries a reusable human subscription token, ambient Sigil, or
raw private Context.

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
