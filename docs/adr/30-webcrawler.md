---
title: 30. Webcrawler
icon: material/spider-thread
---

# :material-spider-thread: 30. Webcrawler

!!! abstract "Context and Problem Statement"
    LychD needs a path to material on the living web, but “web access” is not one capability.
    Search, fetch, extraction, crawling, rendering hostile code, interaction, credential use,
    session custody, screenshots, downloads, and durable admission carry different authority,
    risk, cost, and evidence. Treating them as one magic browser would let a failed read silently
    acquire greater power and would confuse contact with truth.

## Requirements

- **Separated effects:** Search, Fetch, Extract, Crawl, Render, Interact, Session, credential use,
  Screenshot, download, and durable artifact admission remain distinct contracts.
- **Host-minted authority:** Agents may propose a locator or effect. Identity, origin grant,
  policy, consent, and reserved budget come from trusted host state.
- **No implicit escalation:** A redirect, JavaScript requirement, CAPTCHA, authentication
  challenge, payment challenge, provider failure, or quota response cannot authorize another
  effect, identity, credential, retry, or provider.
- **Pinned destinations:** Network providers must defend against SSRF, DNS rebinding, ambient
  proxy and credential use, unbounded redirects, decompression bombs, and private or metadata
  destinations.
- **Hostile-content fencing:** Returned material remains attributed external data. Extraction,
  Markdown conversion, OCR, or screenshotting does not make it true or executable.
- **Truthful custody:** An effect receipt records an attempted effect; a durable `ArtifactRef`
  requires real Reliquary admission and retrieval.
- **Bounded operation:** Every provider must enforce request, byte, time, concurrency, depth, and
  spend budgets with explicit cancellation and crash ambiguity.
- **Optionality:** A profile with no web acquisition is valid.

## Considered Options

!!! failure "Option 1: One automatic Scout"
    A single provider tries lightweight HTTP first and silently escalates to a browser, session,
    credential, paid service, or retry when the first attempt fails.

    This collapses distinct grants, makes refusal an obstacle to overcome, hides disclosure and
    cost, and gives provider behavior authority over policy.

!!! failure "Option 2: One privileged browser service"
    A headless browser handles every web operation from one broadly trusted container.

    Browser isolation reduces reach but never makes blast radius zero. It also pays the resource
    and hostile-code cost for observations that need only a bounded static read.

!!! failure "Option 3: Provider SDKs as policy"
    Firecrawl, SearXNG, provider-native model tools, or another SDK decides fallback, credentials,
    persistence, and routing.

    Such systems may later implement a bounded adapter, but none may own LychD identity,
    destinations, consent, provenance, budget, or artifact admission.

!!! success "Option 4: Separated acquisition effects"
    Scout is a Domain whose independently authorized providers are assembled by Weaver Patterns.
    The first implementation proves one static public-page passage; rendering and interaction
    arrive only after inheriting the common authority and evidence floor.

## Decision Outcome

**The Scout Domain is adopted as a composition of separately authorized acquisition effects.**
There is no sovereign `Scout` package and no provider may upgrade its own grant.

Scout is the common external-observation boundary, not an operator-facing application catalogue.
Bazoš, Google Maps or another geo provider, a merchant catalogue, a shop, and a public menu source
are source/provider adapters beneath Scout even when they expose different APIs, feeds, pages, or
browser surfaces. A consuming Composition owns why the observation matters and what consequence
may follow; the adapter owns only lawful acquisition, normalization, provenance, freshness,
budgets, and source-specific policy.

### 1. The First Passage

The first supported path will be one bounded, unauthenticated HTTPS GET followed by network-free
extraction:

1. An Agent proposes one exact public URL.
2. The host mints Acquisition Authority from a verified principal, canonical Run, operator origin
   grant, fixed policy, consent reference where required, and a worst-case budget reservation.
3. A prepared attempt is committed before the network effect.
4. A static adapter performs a destination-pinned GET without subresources, ambient proxy,
   credentials, cookies, cache, custom headers, link following, or automatic retry.
5. A network-free extractor accepts only bounded HTML, XHTML, or plain text and emits fenced
   external material tied to raw and output digests.
6. A terminal transaction settles budget and disposition. An ambiguous crash becomes
   `unknown_after_crash` until independent evidence reconciles it.

Raw bytes are released after extraction unless a separate Reliquary contract admits them.
Search, Crawl, Render, Interact, Session, credential use, Screenshot, download, paid providers,
caching, and Smith ingestion remain closed until each has its own contract and adversarial
receipt.

### 2. Authority and Provider Selection

The Agent-visible proposal and host-minted Acquisition Authority are different types. A future
provider-selection seam may choose only among providers already eligible for the exact authorized
effect. The Orchestrator participates only when an admitted provider is a managed runtime; it does
not own destination policy, credentials, truth, or artifact admission.

Every redirect is a new destination decision. URL credentials and unapproved schemes fail closed.
Resolution rejects forbidden or mixed address sets, pins the approved destination through
connection, and verifies that the connected peer, TLS identity, `Host`, and SNI agree.

### 3. Evidence Is Not Truth

The authoritative record is the effect receipt: the acting office's account of one attempted
effect and its disposition. The response is a bounded observation. Extraction is a derivation
whose parents and method remain visible. Interpretation or verdict belongs to
**[Riddle (34)](34-evaluation.md)** under declared criteria.

```text
search result != fetched response != extracted statement != trusted fact
fetch != render != interact != credential use
acquired != admitted != understood != trusted != promoted
```

### 4. Active Browsing and Custody

A future renderer must be a dedicated, unprivileged, disposable runtime with an independent
network boundary, Chromium's own sandbox, and no core Pod peers, host mounts, database access,
container-control socket, wallet key, or ambient provider secret. A CAPTCHA or access-control
challenge returns a typed human-required outcome rather than triggering evasion.

Credentials remain opaque, origin-scoped references outside prompts and ordinary telemetry.
Browser profiles belong to one principal, purpose, origin set, and finite lifetime. Downloads
enter quarantine and require media sniffing, digest, provenance, classification, retention,
retrieval authority, and explicit Reliquary admission.

## Delivery Boundary

This ADR accepts architecture, not implementation. LychD currently has no Scout provider,
browser service, acquisition endpoint, Agent tool, custody path, or automatic Toll. The exact
public boundary remains on the **[Scout page](../sepulcher/extensions/scout.md)** and its maintained
**[State of Work subject](../state-of-the-work.md#scout-web-acquisition)**.

## Consequences

!!! success "Positive"
    - Lightweight reads do not inherit browser, credential, session, or payment authority.
    - Provider implementations can evolve behind one explicit acquisition law.
    - Provenance, crash ambiguity, hostile content, and custody remain visible.

!!! failure "Negative"
    - The design needs more contracts and tests than a single crawler wrapper.
    - Dynamic sites, authenticated sessions, downloads, and paid providers arrive later.
    - Destination pinning and browser isolation require maintained security work.
