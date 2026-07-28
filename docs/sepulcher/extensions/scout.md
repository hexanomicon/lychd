---
title: Scout
icon: material/navigation-variant-outline
---

# :material-navigation-variant-outline: Scout

**Purpose.** Scout is the planned boundary through which LychD will discover and acquire material
from the living web without confusing access with truth or a URL with permission.

**Current boundary.** No Scout capability or provider package is available today. There is no
search, fetch, crawl, browser, artifact, or Agent-tool path.
[State of the Work owns the exact Scout delivery boundary](../../state-of-the-work.md#scout-web-acquisition).

**Law.** [ADR 30](../../adr/30-webcrawler.md) owns the accepted separation of web effects:
access never escalates itself, and isolation reduces reach without making browser blast radius
zero.

**Extension form.** Scout is a designed acquisition Domain manifested through separately
authorized search, fetch, extract, crawl, render, interaction, session, and screenshot providers
assembled by Weaver Patterns. No single Scout package or provider receives authority to escalate
between those effects, and the absence of web access remains a valid profile.

> _A Scout may bring a voice from beyond the Circle. It may not grant that voice the throne._

!!! danger "Nothing on this page can be invoked yet"
    No `web.coven`, browser service, web tool, search provider, CAPTCHA solver, screenshot store,
    authenticated browser session, Smith ingestion path, or automatic Toll exists in LychD. The
    sections below define the intended contract, not commands for the current Vessel.

## Nine Tracks Through the Wild

Scout will coordinate separate effects rather than expose one magic browser. They form three
navigational rings, not three shared grants:

- **Read the web.** Search discovers candidate locators. Fetch performs one bounded read. Extract
  transforms already acquired bytes without network access. Crawl owns a bounded frontier, scope,
  pacing, deduplication, expiry, and total budget.
- **Execute the site.** Render runs hostile site code for an observation. Interact clicks, types,
  submits, or uploads. Credential use permits one opaque, scoped reference under
  [Ward](./ward.md) authority. Session custody owns cookies, browser storage, revocation, expiry,
  and destruction for one principal and purpose.
- **Preserve a visual result.** Screenshot requests pixels from a renderer. Durable custody is a
  separate [Reliquary](../../divination/altar/reliquary.md) admission; [Prism](./prism.md) may later
  prepare admitted pixels for a vision model.

Download and archive admission, OCR, and artifact materialization remain adjacent typed contracts,
not permissions hidden inside Fetch or Render.

```text
search result != fetched response != extracted statement != trusted fact
fetch != render != interact != credential use
```

## The First Passage: One Static Public Page

The first implementation should prove one useful path before opening the browser:

1. The Agent proposes one exact public HTTPS URL. It cannot provide its own principal, canonical
   run id, origin grant, consent, or budget.
2. The host combines that proposal with an **Acquisition Authority** minted from the canonical Run
   record, the verified local principal, an operator origin grant, fixed policy and budget
   reservation, and consent reference where required.
3. One committed transaction records a prepared attempt and reserves the worst-case budget. The
   network effect then runs outside that transaction.
4. A static adapter performs a destination-pinned, bounded, unauthenticated GET with no
   subresources, link following, ambient proxy, credentials, cookies, cache, custom headers, or
   automatic retry.
5. A network-free extractor admits only bounded HTML, XHTML, or plain text and returns fenced
   external material tied to raw and output digests.
6. A second transaction settles the budget and terminal disposition. After a crash, a stranded
   attempt becomes explicit `unknown_after_crash` unless independent evidence reconciles it; an
   absent terminal row never authorizes an ambiguous retry.

Raw bytes are not intentionally persisted and are released after extraction. Search, crawl,
render, interaction, credential use, sessions, screenshots, downloads, paid providers, caching,
and Smith ingestion remain closed until each has its own contract and adversarial receipt.

!!! note "Why not begin with the impressive browser?"
    Static acquisition proves the shared floor—identity, destination, SSRF resistance, bounds,
    hostile-content fencing, provenance, cancellation, and truthful failure—without also executing
    a website's program. Render and interaction can inherit that floor without disguising their
    additional authority.

## Contact Does Not Become Truth

Scout uses the same evidence ladder as Oculus:

- The **authoritative record** is an acquisition effect receipt: the acting office's account of
  one attempted effect, its policy and budgets, and its disposition. It does not make returned
  prose true.
- The response is a **bounded observation** of what one server or provider returned at one time.
- Extracted or normalized material is a **derivation** whose parents and method remain visible.
- An **interpretation or verdict** belongs to [Riddle](./riddle.md) under declared criteria.

An effect receipt is not a maintained operator receipt and cannot promote Scout in
[State](../../state-of-the-work.md). The [Phylactery](../phylactery/index.md) may persist the
redacted receipt; Reliquary must admit actual bytes before a durable artifact exists; Oculus may
only correlate and project an allowlisted reference. A digest alone is neither custody nor proof.

## One Passage, Several Gates

The Agent-visible proposal and host-minted Acquisition Authority are different types. The current
`magus:*` Sigil is a contained local-bootstrap identity, not remote authentication. Remote web
acquisition remains closed until Ward can prove the caller.

The future acquisition provider-selection seam may choose only among providers already eligible
for the exact authorized effect. It may not turn “JavaScript required,” a redirect, CAPTCHA,
`401`, `403`, `402`, provider failure, or quota response into permission for a browser, identity,
credential, payment, retry, or different provider. The
[Orchestrator](../../adr/23-orchestrator.md) participates only when an admitted provider is a
managed runtime; it does not own URL policy, credentials, truth, or artifact admission.

## The Laws of the Road

### Destination before connection

Every future network read will normalize and authorize the scheme, hostname, port, and origin;
reject credentials in URLs and unapproved schemes; resolve all addresses and fail when any answer
is forbidden or mixed; pin the approved destination through connection; and verify the connected
peer, TLS identity, `Host`, and SNI agree. Every redirect passes the same gate again. Loopback,
private, link-local, metadata, multicast, DNS-rebinding, ambient-proxy, `.netrc`, TLS-bypass, and
unbounded-redirect paths fail closed.

### External material remains external

Search queries are classified egress payloads. Snippets, HTML, Markdown, PDFs, OCR, accessibility
trees, metadata, and screenshots may carry prompt injection, secrets, falsehood, or hostile
structure. Fetchers and parsers need hard request, redirect, header, byte, decompression, time,
output, and concurrency limits. Extracted text enters
[Context](../../adr/21-context.md) as attributed, fenced data—never as a system instruction or
automatic tool command. Extraction may reduce noise; it cannot make a source trustworthy.

### Refusal is not resistance to overcome

Future crawl policy will identify its user agent, respect robots rules by default, pace each
origin, and record its decision. Robots, site terms, authentication, authorization, and law remain
distinct. A CAPTCHA or bot challenge returns a typed human-required outcome. Scout will not evade
access controls, rotate identities around refusal, or escalate itself into an authenticated
session.

### Credentials and browser state are custody

Credentials remain opaque, scoped references outside prompts and ordinary telemetry. Profiles
belong to one principal, purpose, origin set, and finite lifetime. A future active renderer must
run as a dedicated, unprivileged, disposable unit in a separate network namespace or independently
proved proxy-only egress path, with Chromium's own sandbox enabled and no core Pod peers, host
mounts, database access, container-control socket, wallet key, or ambient provider secret. A
container lowers reach; it never makes browser blast radius zero.

### Bytes need custody before a name

A download enters quarantine, not the Lab or a shell. It needs bounded size, media sniffing,
digest, provenance, classification, retention, retrieval authority, and separate archive-admission
law. The current `ArtifactRef` is metadata only; Scout must not mint a durable artifact reference
until a real custody service has admitted and can retrieve the content.

### Cost is policy, not an HTTP reflex

Every operation will reserve hard request, byte, time, concurrency, depth, and spend budgets.
Remote providers cross the disclosure and credential boundary described by
[Portal](../animator/portal.md), even when their SDK looks local. [Toll](./toll.md) is not
implemented: no price challenge authorizes payment, and no paid provider retries itself.

## Reference Adapters, Never Sovereign Law

External projects can later teach or implement bounded adapters without owning Scout's policy:

- **SearXNG** is a candidate discovery service. Self-hosting the aggregator does not stop its
  configured engines from receiving classified queries, and search results are not fetched
  content.
- **Firecrawl** is a candidate hosted or separately deployed acquisition provider. Hosted use
  discloses requests and content and may cost money; self-hosting adds service, storage, browser,
  security, upgrade, and AGPL obligations.
- **The refreshed upstream Pydantic AI reference** offers provider-native and fallback web tools;
  LychD's installed `pydantic-ai-slim==1.25.1` does not contain these capability APIs.
  Provider-native execution sends the query or URL to the selected model provider. In the
  upstream API, `local` names where fallback code runs, not where data stays: DuckDuckGo still
  receives a search query and local WebFetch still contacts the target. Native execution also
  remains preferred unless explicitly disabled with `native=False`. These helpers are comparison
  or outer-adapter material, not the first Scout implementation. A provider-native result without
  raw bytes, redirect evidence, connected-peer evidence, and digests remains provider-mediated. A
  local-fallback result still is not a Scout Fetch receipt unless an outer adapter captures and
  validates that evidence.

No SDK, hosted service, or model provider may decide LychD's destinations, identity, credentials,
budgets, consent, provenance, or artifact admission.

## Scout, Prism, and Smith

Scout will acquire and attribute. Prism will later materialize visual input for sight.
[Smith](./smith.md) will later propose changes from admitted references under forge, verification,
and consent law. None of these steps implies the next:

```text
acquired != admitted != understood != trusted != promoted
```

That interval preserves another center instead of assimilating it on contact. The web may answer
through the Circle; it does not become the Lich's memory, policy, or body merely by being heard.

> _Next act: prove the first static passage under the
> [Scout delivery boundary](../../state-of-the-work.md#scout-web-acquisition) before opening any
> stronger effect._
