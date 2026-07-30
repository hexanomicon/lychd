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
Screenshot, Download,** and **Artifact Admission** needs its own host-owned grant and ceiling.
Authentication, CAPTCHA, payment, quota, robots denial, provider failure, cancellation, or a
challenge is a terminal typed result: no identity rotation, provider switch, retry, spend, or
effect escalation follows. No-web profiles are valid and confer no ambient egress.

## The first passage

The first designed passage is one unauthenticated static HTTPS GET and network-free extraction:

1. An Agent proposes one exact URL. The host validates its principal and Run, mints a one-effect
   destination grant, selects an eligible static provider, reserves worst-case budget, and
   durably records `prepared` before I/O.
2. The provider pins and performs one GET: no subresources, JavaScript, cookies, cache, URL
   credentials, `.netrc`, ambient proxy, custom headers, automatic retry, or rendering.
3. A network-free extractor accepts only allowed HTML, XHTML, or plain text; it records raw and
   output digests, extractor identity, and loss, then returns fenced attributed text.
4. Settlement records disposition and usage. A prepared attempt after a crash is
   `unknown_after_crash`; without an independent terminal record there is no blind retry.

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
principal- and origin-scoped references outside prompts and telemetry.

## Delivery Boundary

**State: Designed. Scout has no delivered acquisition capability.** There is no Scout built-in,
configuration, provider, route, Agent tool, fetcher, extractor, robots/rate policy, SSRF pinning,
receipt, browser, quarantine, or Reliquary. Installed `httpx` serves other control-plane calls;
`selectolax` is test-only. Generic-runtime “crawler” tests prove only that no capability is
invented. `ArtifactRef` proves metadata, not custody. Source, configuration, adversarial
network/parser tests, and an updated [State of Work](../state-of-the-work.md#scout-web-acquisition)
record are required before delivery. The [Scout topic](../sepulcher/extensions/scout.md) orients
the reader.

## Consequences

!!! success "Positive"
    Static reads do not inherit browser, credential, payment, storage, or interpretation authority.
    Redirect, provenance, hostile-content, and custody failures stay visible and recover only by a
    newly admitted effect.

!!! failure "Negative"
    Safe acquisition requires more than HTTP and HTML libraries. Dynamic, authenticated, paid, and
    durable material remains unavailable until its separate adversarial boundaries pass.
