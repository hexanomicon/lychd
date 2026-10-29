---
title: Scout source acquisition study
icon: material/rss
---

# Scout: search, feeds and the Bazoš passage

**Maturity: candidate study, reviewed 18 October 2026.** This study selects the next experiment;
the separately qualified RSS extractor is recorded in State. Native feed acquisition/workflow,
monitoring and standing authority remain outside this study.
[Scout](scout.md), [ADR 30](../../adr/30-webcrawler.md) and
[State](../../state-of-the-work.md#scout-web-acquisition) retain those boundaries.

## Choose the source surface before adding a service

| Need | Smallest useful path | Current boundary |
| --- | --- | --- |
| Understand one known public page | Existing static HTTPS Fetch and isolated HTML/text Extract | Opt-in public-page workflow; actual host/profile qualification remains necessary |
| Observe recent Bazoš listings | One advertised category RSS feed, then local extraction/filtering | The selected finite Scavenger application and its dated public-native observations are recorded in State; recurring watching remains unfinished |
| Discover sources across the web | SearXNG, one qualified engine and one result page | No admitted engine, Rune or adapter ships; upstream-request mediation remains a prerequisite |
| Read a page whose useful content requires JavaScript | Separately admitted Fetch + Render + Extract | Crawl4AI remains a later isolated candidate, not an automatic fallback |

Choose the path by the observation the application needs. A known Bazoš feed can supply a finite
listing observation without first building general Search. Search can discover other sources,
and rendering can make a particular JavaScript page readable, but each adds a separate contact
and qualification problem. Progress on the feed therefore neither waits for nor demonstrates
Search or Crawl.

## What the live source established

On 18 October 2026, one bounded read of the public [PC category](https://pc.bazos.sk/) returned
HTTP 200 and 45,992 bytes of UTF-8 HTML. Its own navigation advertised
[the PC RSS feed](https://www.bazos.sk/rss.php?rub=pc). A separate single read of that exact feed
returned HTTP 200, `text/xml; charset=utf-8`, and 33,385 bytes. These are dated research
observations, not a maintained deployment receipt or a compatibility promise.

The [category robots](https://pc.bazos.sk/robots.txt) and
[main-host robots](https://www.bazos.sk/robots.txt) then disallowed search/filter URL patterns
including `hledat`, location and price parameters. The category root and advertised PC feed
were not excluded by their default rules. Recheck the exact host and locator before an admitted
contact; a linked URL or historical robots observation is not an effect grant. Do not substitute
filtered search URLs, mobile identities, extra pages or another endpoint after refusal.

The existing fixed Scout extractor processed the acquired category HTML in its isolated,
network-denied child and returned 11,461 bytes of text; the child was reaped. Supplying the RSS
response under its actual `text/xml` type correctly refused before child launch. This separates
the dated useful HTML path from the then-missing XML path. The later separate RSS profile
now extracts bounded RSS 2.0; this did not widen that old header or the public-page workflow. Recasting XML as HTML, ignoring the media check or
running a second parser inside Core would conceal that gap.

The current HTML strategy deliberately drops attributes, including link targets. Its text
projection can support a bounded page answer; it is not already a structured listing catalogue.

## What other projects contribute

The [Bazoš dataset project](https://github.com/kukas/bazos_dataset) publishes a
[feed-based scraper](https://github.com/kukas/bazos_dataset/blob/main/bazos_scraper.py).
The useful pattern is to read category feeds, retain source identity and observation time, and
compare entries locally. Its historical Czech dataset does not establish current Slovak coverage,
and its repeated polling or retry behavior does not supply LychD authority.

The [Bazoš MCP client](https://github.com/andrijdavid/bazos-mcp/blob/main/src/bazos-client.ts)
uses a different API path with a generated device identifier and User-Agent. This is comparison
material, not the selected acquisition mechanism. No upstream scraper, MCP server, credential
store, retry policy or implementation is incorporated by this study.

The official [SearXNG Search API](https://docs.searxng.org/dev/search_api.html) supports form POST
and explicitly enabled JSON output; public instances can disable it. Its query still reaches
external engines. LychD's selected design therefore needs more than an HTTP JSON wrapper:
one qualified engine, a restricted query dialect, immutable configuration and the exact
pre-transmission transport gate in ADR 30. Do not count installing a stock container as that proof.

## Feed experiment: one feed, one attributed digest {#next-vertical-slice-one-feed-one-attributed-digest}

The advertised PC RSS feed supplied the finite experiment below. The selected Scavenger
application and dated ordinary-native observations now have their evidence in
[State](../../state-of-the-work.md#scout-web-acquisition). Its title/link-only consumer contract
belongs to [Market](../../compositions/scavenger/market.md#finite-feed-observation), including
permanent allowance, custody and deletion. The baseline below explains the experiment; it does
not widen the old static profiles or replace that selected consumer contract.

The experiment's acceptance baseline is:

- One exact host-admitted locator and finite Fetch/Extract ceilings, no pagination, subresource,
  redirect discovery, retry, browser, paid service or publisher contact.
- Parsing in the existing kind of isolated child, with construction-time element/depth limits,
  bounded item/field/output counts and existing hard time/resource ceilings. DTDs, external
  entities, entity expansion, malformed XML, over-limit and truncated input must refuse.
- Extractor-level plain title/summary plus original item locator, publisher identifier/date as
  claims, source attribution, observation time and declared omissions. The selected Scavenger
  consumer discards summaries and publisher identifiers/dates, retaining title/link and necessary
  attribution only. No source-authored markup or instructions
  gain authority. Returned links are data; contacting one needs a fresh destination/effect decision.
- Independent ordinary and hostile fixtures sealed before a constructor candidate. Then qualify
  the actual transport/child combination and current native admission path, retaining refusals and
  observed cleanup. A synthetic parser test alone cannot qualify live acquisition.
- Local deduplication and filtering over the admitted observations, with honest coverage. No match
  means no match in that finite response; it never means no matching listing exists on Bazoš.
  The consuming application owns suitability criteria and any proposed consequence.

Begin by returning an attributed digest without a model, and measure that result against the
baseline above. It gives model ranking, semantic extraction, or a browser a concrete result to
improve on. Even then, a price parsed from source prose is a derived claim: the observation
establishes neither current availability nor seller trust.

Repeated watching is a later application policy: explicit purpose, exact feed, cadence, finite
contact/retention budget, revocation and uncertain-attempt reconciliation. Each poll needs current
admission; an idle loop cannot manufacture a new allowance. Retaining prior entries or bodies
needs the ordinary custody owner, not a private cache hidden in an Agent's history.

The selected Altar presents source/time, coverage, whole-field counts, local filters and distinct
new-observation/deletion actions. State records the separate synthetic-browser, native API and
[dated authenticated retained-field browser evidence](../../state-of-the-work.md#scout-web-acquisition).
That finite functional observation does not establish a persistent deployment or hostile-browser
safety. A new fetch and a local re-filter must remain distinguishable.


## SearXNG transport cut — 18 October 2026 {#searxng-transport-cut}

The reviewed upstream source is pinned to
[`1c10abe2d`](https://github.com/searxng/searxng/commit/1c10abe2d3e4ab7ddcc4e9da1a7d07dc7ca7f8f4).
Its online processor separates engine request preparation, network exchange and response parsing.
The lower [`Network.call_client`](https://github.com/searxng/searxng/blob/1c10abe2d3e4ab7ddcc4e9da1a7d07dc7ca7f8f4/searx/network/network.py#L271)
still retries the first connection error without decrementing its retry counter. In a dated
offline reproduction of that exact method, `retries=0` plus a controlled disconnect followed by
success causes two client acquisitions and two request calls. Separate controls cover repeated
connection errors, immediate success and a different request exception. No network occurred.

A private, separately licensed service prototype replaces that direct path before client
acquisition and refuses `get_client` itself. Its actual patched method ASTs and coroutine hook
pass six offline cases: absent context, streaming refusal, one-use success, terminal failure,
consumption before a suspended/cancelled call, and direct-client refusal. A narrow independent
static review found no P1/P2 defect within that declared scope. The
[dated observation](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/searxng-transport-cut-2026-10-18.json)
records exact source, patch, script and result hashes. The prototype is outside Core and is not
an installed service, authenticated channel, host grant or containment boundary.

Engine eligibility also needs source inspection. At this same pin,
[`mojeek.request`](https://github.com/searxng/searxng/blob/1c10abe2d3e4ab7ddcc4e9da1a7d07dc7ca7f8f4/searx/engines/mojeek.py#L102)
obtains a CAPTCHA-derived cookie through auxiliary challenge/verification calls when uncached.
That flow is outside the first proposed public-search passage; no challenge was executed.
The [`DuckDuckGo HTML module`](https://github.com/searxng/searxng/blob/1c10abe2d3e4ab7ddcc4e9da1a7d07dc7ca7f8f4/searx/engines/duckduckgo.py#L362)
is only a candidate: first-page preparation uses a form POST, and its response parser raises on
a CAPTCHA but returns empty results for HTTP303. The trusted bridge must therefore reject a
redirect before parser invocation rather than record a clean miss. Regional/time filters can
add cookies, and debug diagnostics include query-bearing data. No live engine or parser
qualification follows from reading those functions.

To turn the prototype into an implementation, preserve the transport cut and connect it to
host authority. That requires a typed, authenticated request/response channel, host-authored
final bytes, Search-specific preparation, current disclosure admission, and independent denial
of direct service egress. Existing native Scout authority admits only fixed page/RSS FETCH
claims; changing their label cannot authorize Search.

Then constrain and qualify the actual request and response path: use the pinned SearXNG parser
to refuse engine/language/category/timeout/bang/lucky directives, qualify one exact engine and
response wrapper, and retain query-bearing diagnostics as restricted evidence. The
[accepted Search contract](../../adr/30-webcrawler.md#searxng-search-contract) owns these
requirements. Neither a working JSON endpoint nor this offline prototype delivers Search, and
neither can reset the retained feed's spent budget.


## Full service fixture: context must cross the dispatcher

A separate [dated local observation](https://github.com/hexanomicon/lychd/blob/main/tests/fixtures/scout/searxng-service-fixture-2026-10-18.json)
now exercises the complete pinned upstream web application, not just its processor. Every case
actually checks authentication and invalid method/input refusals before accepting one fixed query.
The original dispatcher loses the host-exchange context: the baseline refuses before exchange or
parser invocation. A narrow `copy_context` prototype crosses the real dispatch thread and asyncio
loop, sends one host-sealed POST through pinned TLS to an isolated fixture, and returns two exact
ordered title/snippet/locator observations through the real DuckDuckGo parser and JSON encoder.
A separately admitted HTTP 303 response refuses before parsing and causes no follow-up request.

Bootstrap requires the complete pinned defaults, removal of every default engine before adding
the sole selected engine, explicit empty plugin replacement and an actual Preferences check
before readiness. Earlier unsupported-CLI and incomplete-default attempts remain failed.
All three later cases have independent process/thread, unit, cgroup, socket and key closure.
Actual stderr still reports favicon, limiter and Unix-socket/IP diagnostics; no source IP is
invented. The narrow entropy-device bind permits read and write, although the experiment writes
no device bytes. IPv6 and persistent service reuse remain unqualified.

This privately isolated prototype is not shipped Core code, a live-engine receipt or native
Search. Production still needs Search-specific preparation and current disclosure/final-byte
admission, a receiving normalizer, admitted lifecycle and a permanent allowance transition that
preserves old counters and unknown reservations. A fresh database cannot manufacture a reset
for an already admitted host. The existing finite RSS route remains independently useful for
Bazoš; it does not need this service.
