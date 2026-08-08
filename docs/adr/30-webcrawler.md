---
title: 30. Webcrawler
icon: material/spider-thread
---

# :material-spider-thread: 30. Webcrawler

!!! abstract "Context and Problem Statement"
    Web acquisition crosses an untrusted network and returns untrusted bytes. Search, fetch,
    extraction, crawling, rendering, interaction, credentials, sessions, and storage are distinct
    effects; failure may never authorize a stronger one. **Scout** may bring a voice from beyond
    the Circle. It may not grant that voice the throne.

## Decision

Scout is the acquisition Extension Domain, not a crawler service or a Composition. A provider
supplies mechanism only; the host binds an Agent's proposed locator to principal, Run, effect,
destination scope, consent, provider, and budget. Scout owns acquisition, attribution, freshness,
and source policy—not interpretation, truth, autonomy, or consequence.

Each of **Search, Fetch, Extract, Crawl, Render, Interact, Credential Use, Session Custody,
Screenshot, Download,** and **Artifact Admission** needs its own host-owned `ScoutEffectGrant` and ceiling.
Authentication, CAPTCHA, payment, quota, robots denial, provider failure, cancellation, or a
challenge is a terminal typed result: no identity rotation, provider switch, retry, spend, or
effect escalation follows. No-web profiles are valid and confer no ambient egress.

### Provider, Animator, and effect-grant boundary

A Scout **Provider** names one admitted acquisition mechanism. An [Animator](../sepulcher/animator/index.md)
may manifest that mechanism as a local Soulstone or remote Portal, but it does not replace Scout:

- the Animator Rune, adapter, probe, and capability declaration establish what service exists and
  whether it is ready;
- the Scout provider binding declares the exact acquisition effects that service may implement;
- a Dispatcher `CallGrant` or `JobGrant` exposes only the exact technical surface and lease; a
  separate `ScoutEffectGrant` authorizes each Search, Fetch, Extract, Crawl, Render, or other effect;
- a provider call that necessarily combines effects may run only when every constituent effect grant is
  present. A convenient scrape endpoint never merges those grants into one authority.

An Animator-owned `ToolConnector` therefore cannot expose a provider's raw SDK, MCP server, REST
surface, CDP session, or browser automation API directly to an Agent. The Agent-facing tool is
Scout-owned and host-mediated: it validates the current effect grants, sends one adapter-authored bounded
request, normalizes the response, and settles the Scout receipt. Animator registration without an
effect-specific Scout provider contribution grants no acquisition authority.

### First-party mechanism policy

LychD's first-party web path must remain useful without a paid remote service. The accepted
mechanism sequence is:

| Mechanism | Manifestation | First-party office |
| --- | --- | --- |
| Native static passage | trusted local Scout code, with isolation added when evidence requires it | one bounded public-HTTPS Fetch followed by network-free Extract |
| [SearXNG](https://github.com/searxng/searxng) | digest-pinned Soulstone behind a native adapter | selected Search provider; locators and attributed snippets only |
| [Crawl4AI](https://github.com/unclecode/crawl4ai) | digest-pinned, separately isolated Soulstone | experimental candidate for one exact public-HTTPS Fetch + Render + Extract passage |
| [Firecrawl](https://github.com/firecrawl/firecrawl) self-hosted | no selected manifestation | deferred comparison candidate, admitted only if it later proves a material advantage over Crawl4AI under the same effect and containment contract |
| [Browserless](https://github.com/browserless/browserless) | no selected manifestation | no first-party raw CDP, Playwright, function-execution, or download adapter; future comparison must satisfy the same narrow renderer contract |
| Paid web-acquisition API, including Tavily and hosted crawler/browser services | operator-owned private Portal extension | no first-party built-in adapter or automatic compatibility promise |

SearXNG is Search, not Fetch. Its result URL remains an observation and needs a new Fetch effect grant
before contact. Its engine catalogue, parsers, suspension policy, and upstream maintenance remain
inside the separate service; LychD owns the Rune, exact JSON profile, ingress authentication,
egress observation, result normalization, probe, and conformance suite.

Crawl4AI's name grants no Scout Crawl authority. The initial candidate has no frontier, arbitrary
JavaScript, hooks, LLM extraction, credentials, cookies, persistent session, screenshot, download,
artifact custody, or generic MCP surface. It receives one exact URL only after the host holds the
separate Fetch, Render, and Extract effect grants. Promotion requires an authenticated narrow API, an
immutable image, a sandboxed browser, a dedicated renderer containment zone, independently gated
destination egress, strict time/process/byte/output ceilings, a license/SBOM receipt, and
real-browser adversarial tests.

Firecrawl is not carried alongside Crawl4AI merely as optional duplication. Its self-hosted stack
remains deferred while it couples more acquisition effects and operational services than the
selected passage needs. Reconsideration requires evidence of materially better coverage,
reliability, or containment at comparable authority and operating cost; cloud Firecrawl remains a
paid private-Portal concern under the rule above.

Browserless is not selected as a second browser backend. A broad CDP or Playwright connection hands
the caller more authority than the first renderer passage, while a service-specific REST facade
still needs the same Scout effect grants, destination gate, containment, and output limits. It returns to
comparison only for an identified gap that Crawl4AI cannot satisfy; adapter multiplicity is not a
goal.

### Attempt layers and crash semantics

The Scout-owned effect attempt carries principal, Run, exact effect grants, destination, provider
binding, budget, acquisition disposition, and receipt semantics. A bounded synchronous Scout
effect enters `prepared` before I/O. An Animator-backed implementation additionally holds a scoped
`CallGrant`; a native host-owned adapter pins its exact Scout provider/adapter binding and uses no
Dispatcher lease. Neither creates a `ServiceJobAttempt@1`. If the process dies before settlement,
Scout records `unknown_after_crash` and does not replay the effect without independent evidence.

An asynchronous crawl or render admitted through `JobGrant` keeps that Scout domain job and layers
it over Core's [`ServiceJobAttempt@1`](14-workers.md#service-job-attempts-designed). Its
`unknown_after_crash` domain disposition maps to the mechanical attempt's `INDETERMINATE` state;
recovery reconciles the same capability-backed execution binding and never invents a second
submission.

No provider is a fallback. One prepared Scout effect attempt binds one selected provider and
profile. A static page that needs JavaScript, an exhausted Search provider, or a renderer failure
settles with that outcome; another provider or stronger effect requires a newly admitted attempt.

### Integration, not vendoring

A **native adapter** means LychD-owned Rune schemas, provider binding, probe, request allowlist,
normalizer, receipts, and conformance tests. It does not mean copying a search engine, crawler, or
browser service into the MPL-covered core. Upstream services retain their own source, image,
license, release cadence, and process boundary. Small useful patterns may enter through
[Assimilation](35-assimilation.md) with provenance and independent expression; entire engine
catalogues and service internals do not.

## The first passage

The first designed passage is one unauthenticated static HTTPS GET and network-free extraction:

1. An Agent proposes one exact URL. The host validates its principal and Run, mints a one-effect
   destination grant, selects an eligible static provider, reserves worst-case budget, and
   durably records the Scout effect attempt as `prepared` before I/O.
2. The provider pins and performs one GET: no subresources, JavaScript, cookies, cache, URL
   credentials, `.netrc`, ambient proxy, custom headers, automatic retry, or rendering.
3. A network-free extractor accepts only allowed HTML, XHTML, or plain text; it records raw and
   output digests, extractor identity, and loss, then returns fenced attributed text.
4. Settlement records disposition and usage. A prepared bounded-call Scout effect attempt after a
   crash is `unknown_after_crash`; without an independent terminal record there is no blind retry.

Wire bytes, decoded bytes, expansion ratio, parse work, output, headers, time, redirects, rate,
concurrency, depth, requests, and spend are separately bounded. `Content-Length` and
`Content-Type` are hints. Mismatch, truncation, unsupported media, or any limit failure refuses.
Crawl, when admitted, adds a finite deduplicated frontier, page/depth budget, per-origin
scheduler, identifying agent, and fail-closed robots evaluation; robots is neither authentication,
site terms, nor legal permission.

## Destination and data boundary

Every initial URL, redirect, and new connection is independently authorized: canonical HTTPS
scheme, hostname, port, and origin only; no userinfo or unsupported scheme. Resolution runs
without ambient proxy or credentials and rejects mixed or forbidden addresses (loopback, private,
link-local, multicast, unspecified, and metadata). The approved address is pinned through the
connection; connected peer, TLS certificate, SNI, and `Host` must match. Redirects are manual,
bounded, loop-checked, and re-gated. An HTTP client or crawler SDK alone cannot establish this
SSRF/DNS-rebinding boundary.

An acquisition receipt names the effect, principal/Run, provider/version, policy, locator and
redirects, destination evidence, time, disposition, media/size, usage, and raw digest. It proves
an attempted effect, not a correct response. Responses and derivations remain attributed data:

```text
locator != response != derived statement != trusted fact
acquired != admitted != understood != promoted
```

They are never instructions, code, policy, or truth. Interpretation belongs to
[Riddle (34)](34-evaluation.md) or the consuming Composition.

## Custody and stronger tracks

A digest or receipt is not an artifact. Bytes stay ephemeral unless custody verifies digest,
media type, size, classification, retention, retrieval authority, and storage, then returns a
retrievable `ArtifactRef`. Download arrival creates neither a workspace nor an artifact; it enters
bounded quarantine. Render, Interact, Credential Use, Session Custody, Screenshot, and Download
remain Designed. JavaScript or a challenge returns refusal or `human_required`, never a browser.

Any future renderer needs a finite destination/egress grant and isolation from Core peers, host
paths, databases, control sockets, wallets, and unrelated secrets. Credentials are opaque,
principal- and origin-scoped references outside prompts and telemetry. A browser-bearing
Soulstone may not join the shared `lychd.pod`; it needs a dedicated rootless containment and
network zone whose only target egress crosses the Scout gate.

## Delivery Boundary

**State: Designed. Scout has no delivered acquisition capability.** There is no Scout built-in,
configuration, provider, route, Agent tool, fetcher, extractor, robots/rate policy, SSRF pinning,
receipt, browser, quarantine, or Reliquary. Installed `httpx` serves other control-plane calls;
`selectolax` is test-only. Generic-runtime “crawler” tests prove only that no capability is
invented. `ArtifactRef` proves metadata, not custody.

The current Extension Context has no Scout-owned provider contribution surface; Animator
capability synthesis still requires a model-shaped identity; `ToolConnector` hydration is
Animator-wide rather than capability/effect-scoped; and current Soulstone compilation joins the
shared Pod. Those are implementation blockers, not permission to approximate the boundary with a
raw provider tool. Source, configuration, adversarial network/parser/browser tests, and an updated
[State of Work](../state-of-the-work.md#scout-web-acquisition) record are required before delivery.
The [Scout topic](../sepulcher/extensions/scout.md) orients the reader.

## Consequences

!!! success "Positive"
    Static reads do not inherit browser, credential, payment, storage, or interpretation authority.
    Redirect, provenance, hostile-content, and custody failures stay visible and recover only by a
    newly admitted effect. Search-engine and browser maintenance stay behind replaceable service
    protocols, while the free local first-party path remains coherent.

!!! failure "Negative"
    Safe acquisition requires more than HTTP and HTML libraries. Dynamic, authenticated, paid, and
    durable material remains unavailable until its separate adversarial boundaries pass. Operators
    choosing paid web providers own a private adapter, its compatibility, and its provider contract.
