---
title: 30. Webcrawler
icon: material/spider-thread
---

# :material-spider-thread: 30. Webcrawler

!!! abstract "Context and Problem Statement"
    Web acquisition crosses an untrusted network and returns untrusted bytes. Search, fetch,
    extraction, crawling, rendering, interaction, credentials, sessions, and storage are distinct
    effects; failure may never authorize a stronger one. [Scout](../sepulcher/extensions/scout.md)
    binds each acquisition attempt to its admitted effect and retains its source attribution.

## Decision

Scout owns acquisition: mechanics, attribution, freshness, and destination/contact policy.
It is an Extension Domain, not a crawler service or Composition.
[The first passage](#the-first-passage) follows a bounded static read from a proposed URL to
attributed text. A provider supplies the mechanism. The host binds the locator proposed by an
Agent or admitted application Pattern to principal, Run, effect, destination scope, consent,
provider, and budget. The consuming application still owns source eligibility, interpretation,
truth, autonomy, and consequence.

Each of **Search, Fetch, Extract, Crawl, Render, Interact, Credential Use, Session Custody,
Screenshot,** and **Download** needs its own host-owned `ScoutEffectGrant` and ceiling. **Artifact
Admission is a separate custody-owner effect**, not an eleventh Scout track: Scout may hand off the
quarantine identity and acquisition receipt, but the custody owner validates classification,
retention, retrieval authority, and exact bytes, and alone returns the durable artifact reference.
Neither the application eligibility decision nor a Scout grant can pre-approve that custody
judgment.

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

The designed contribution binds one provider identity/revision, host-assigned Registrant,
semantic interface and operation, exact required effects, immutable profile and dialect-driver
references, and conformance evidence. Its execution binding selects either a native adapter or
one exact Animator capability. These references resolve before the Scout-owned store seals with
the [extension assembly](05-extensions.md#2-the-registration-surface-the-extension-context).
Conflicting ownership, unresolved references, and post-assembly mutation refuse. Scout binds the
[Dispatcher's interface/profile/driver contracts](22-dispatcher.md); it does not create another
capability registry or disguise Search as a model.

Configuration selects an admitted binding and may narrow its ceilings. It cannot contribute code,
an endpoint, extra engine, or new effect through request parameters. Preparation retains the
binding and effective configuration digests; replacement requires a new admitted attempt, and
executable changes follow the existing Vessel-generation boundary. A readiness probe checks its
declared local service surface only. A real search probe needs its own Search and egress admission.

### First-party mechanism policy

LychD's first-party web path must remain useful without a paid remote service. The accepted
mechanism sequence is:

| Mechanism | Concrete form | First-party office |
| --- | --- | --- |
| Native static passage | trusted local Scout code with a disposable, network-denied parsing/extraction child | one bounded public-HTTPS Fetch followed by network-free Extract |
| [SearXNG](https://github.com/searxng/searxng) | digest-pinned Soulstone behind a native adapter | selected Search provider; locators and attributed snippets only |
| [Crawl4AI](https://github.com/unclecode/crawl4ai) | digest-pinned, separately isolated Soulstone | experimental candidate for one exact public-HTTPS Fetch + Render + Extract passage |
| [Firecrawl](https://github.com/firecrawl/firecrawl) self-hosted | no selected concrete form | deferred comparison candidate, admitted only if it later proves a material advantage over Crawl4AI under the same effect and containment contract |
| [Browserless](https://github.com/browserless/browserless) | no selected concrete form | no first-party raw CDP, Playwright, function-execution, or download adapter; future comparison must satisfy the same narrow renderer contract |
| Paid web-acquisition API, including Tavily and hosted crawler/browser services | operator-owned private Portal extension | no first-party built-in adapter or automatic compatibility promise |

SearXNG is Search, not Fetch. Its result URL remains an observation and needs a new Fetch effect grant
before contact. Its engine catalogue, parsers, suspension policy, and upstream maintenance remain
inside the separate service; LychD owns the Rune, exact JSON profile, ingress authentication,
enforced egress mediation, result normalization, probe, and conformance suite. The
[Search contract](#searxng-search-contract) below defines that mediation; an ordinary SearXNG
container does not already satisfy it.

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
it over Core's [`ServiceJobAttempt@1`](14-workers.md#service-job-attempts). Its
`unknown_after_crash` domain disposition maps to the mechanical attempt's `INDETERMINATE` state;
recovery reconciles the same capability-backed execution binding and never invents a second
submission.

No provider is a fallback. One prepared Scout effect attempt binds one selected provider and
profile. A static page that needs JavaScript, an exhausted Search provider, or a renderer failure
settles with that outcome; another provider or stronger effect requires a newly admitted attempt.

The designed [trusted local profile](38-iam.md#trusted-local-scout-profile) commits one unique
execution claim and atomically reserves its complete worst-case allowance against both binding
and shared host limits before network I/O. The claim binds the retained Run, exact preparation and
consent, provider/profile, contact plan, policy and revocation generations. An exact duplicate
reads retained status; changed bindings refuse. No database transaction spans network I/O, and
the current handoff gate rechecks authority after awaited claim preparation. Restart cannot turn
the reserved allowance into another execution permit.

Each handoff decision is made before its byte transfer. Its bounded restricted evidence may
be buffered until terminal settlement; successful settlement persists that evidence and measured
usage before releasing eligible reservations. A crash may therefore leave the durable claim and
reservation without exact contact detail. Such an attempt remains `unknown_after_crash`, never a
claim that no bytes were sent, a refunded budget, or permission to replay. Unproved socket or child
termination keeps the reservation held.

### Workflow handoff

The hosting Pattern pins a stable acquisition request identity before execution and retains its
attempt/receipt references in typed state. A Graph node execution occurrence is trace identity,
not the acquisition idempotency key: hardware re-entry can create another occurrence for the same
logical request. A repeated request with changed bindings refuses; an exact repeat reads retained
status without obtaining a second execution permit.

An Animator-backed station resolves readiness and its scoped technical lease before Scout
preparation. Hardware waiting therefore cannot leave a prepared acquisition to be resubmitted on
re-entry. Native static acquisition needs no model grant. Scout retains authority and reservation
truth in its own attempt store; Run, Step and orchestration events carry safe correlation only.

Workflow state never retains live grants, provider handles, or acquired bodies. An acquisition
receipt cannot recover ephemeral bytes after a park or restart. A workflow that needs those bytes
later must obtain separate custody admission and recheck current retrieval authority; otherwise it
returns material-unavailable without refetching. Context receives a bounded, attributed data
projection with its budget and influence accounted for before a model request. Neither dynamic
instructions nor ordinary history silently become a storage path for web material. The
[Archive answer workflow](../state-of-the-work.md#karma-semantic-memory) is a projection precedent, not
Scout delivery or permission to auto-promote sources into memory.

### Native adapters and upstream services {#integration-not-vendoring}

A **native adapter** is the LychD-owned side of an integration: Rune schemas, provider binding,
probe, request allowlist, normalizer, receipts, and conformance tests. The upstream search engine,
crawler, or browser service keeps its own source, image, license, release cadence, and process
boundary. Native integration does not copy that engine into the MPL-covered core. Small useful
patterns may enter through [Assimilation](35-assimilation.md) with provenance and independent
expression; entire engine catalogues and service internals may not.

### Advertised feeds

A known public feed can answer a purpose through an explicitly admitted Fetch and Extract
passage, before a search service or browser is needed. Its publication supplies a proposed locator
only. Contact, parsing, custody, and recurring polling need their own authority. The feed also
needs a qualified media and extraction profile because the current native HTML/plain-text profile
does not admit XML. Item locators remain bounded returned data, never permission for further
fetches. The consuming application owns local filtering and suitability; repeat watching needs
current admission and finite standing policy.

The [Scout source study](../sepulcher/extensions/scout.md#source-acquisition-study) records a Bazoš RSS
premise and the next qualification obligations. It is a candidate study, not an admitted feed
profile or delivery evidence.

### Model-free native feed handoff

The selected native `rss-public-feed@1` binding uses `native-static@1` and the qualified
`scout-rss-extract@1` worker. Its HTTP profile sends only the fixed RSS/XML Accept set and accepts
only `text/xml`, `application/xml` or `application/rss+xml`, with strict UTF-8 and at most 1 MiB
decoded representation, 2 MiB response wire body and the existing bounded HTTP/gzip/framing
rules. The profile is selected by the host-owned binding before contact, never inferred from a
response header. The old static serializer/parser and page binding retain their exact media and
byte contracts. This first feed follows no redirect, retry, item link, script or subresource.

A model-free consumer binds its exact admitted Pattern, purpose, application request and
projection/custody profile independently of any later model capability. It gets no placeholder
capability, Dispatcher lease or ServiceJobAttempt. The unversioned page preparation/review encoding
remains frozen; a distinct closed feed encoding retains the consumer binding and explicitly no
model grant. Unknown or mixed encodings refuse. Run, consent, claim, profile and budget identity
remain in the existing Scout store; the first profile preserves the one-active-binding/fresh-profile
database boundary and refuses retained incompatible budgets without rewriting them.

The consuming Composition owns its retained result. Scout's transient feed material is consumed
only by that exact admitted consumer under current CONSUME authority, including after waits and
before result adoption. It does not acquire storage authority from Fetch or Extract. Extraction
settlement uses a positive type-specific metadata projection: profile/media, source/record/text
digests where applicable, strategy, transformations and bounded counts. It never serializes feed
channel/items, titles, links, summaries or publisher claims by removing only a `text` key.
Contact attribution remains separately owned restricted network evidence.

The [Scavenger finite observation](../compositions/scavenger/market.md#finite-feed-observation)
selects the concrete native consumer and its whole-field custody/deletion/recovery contract.
A retained receipt cannot reconstruct missing material or authorize refetch. Network/native/consumer
qualification remains separate from the RSS extraction mechanism.

## SearXNG Search contract

The designed `searxng-search@1` profile supports one query, one qualified engine, one result page,
and at most ten locator observations. A later multi-engine profile must qualify each recipient
and their aggregate disclosure budget. The Agent proposes query text, a supported language/time
filter, and a result limit within the profile. The host owns provider selection, engine identity,
endpoint, credentials, request parameters, deadlines, and grants. Unknown fields and unsupported
filters refuse before contact; an arbitrary provider-options dictionary is not part of the tool.

The adapter uses authenticated `POST /search` with explicitly enabled JSON output, no caller
cookies or preferences, and no redirect following. The effective service configuration positively
selects the engine; inherited defaults, autocomplete, favicon retrieval, answerers, and optional
plugins cannot add contacts or outputs. Query syntax that selects engines, categories, languages,
external bangs, or lucky redirects is refused by the pinned parser contract, not guessed away
with an unqualified regular expression. Typed filters are compiled only where that engine proves
support. These restrictions also apply at service admission and transport, independently of input
validation. The local service address comes from its registered control-plane binding; it does
not grant an exception for public acquisition to contact private destinations.

### Query disclosure and engine transport

Query derivation preserves [Context influence and privacy labels](21-context.md#privatization-and-the-privacy-cut).
A local search service still discloses to remote engines. Before each upstream transmission,
[Security](09-security.md#portal-privatization-and-egress) must admit the exact final request:
recipient and custody route, canonical target and wire digest, source influence, disclosure basis,
policy, expiry, and remaining budget. Raw-eligible public queries still require this decision;
URL encoding is not anonymization. The local ingress request never authorizes unknown fan-out.

The selected integration requires an explicit cooperative request-mediation seam: the service
prepares a bounded engine request, the trusted transport admits its final bytes and sends it, and
the service receives the bounded response for parsing. Independent containment denies direct
service egress. Query-bearing URLs, headers, bodies, initialization, auxiliary requests and
redirects must all cross that seam under an exact admitted contact plan. No transparent TLS
interception, ambient proxy, destination allowlist alone, or after-the-fact observation substitutes
for the Gate. The adapter must account for transport-generated fields before sealing the request.
No compliant upstream hook, engine profile, image, or containment implementation is claimed here.

The first profile has no retry, redelivery, proxy/identity rotation, page expansion, or fallback.
It reserves a finite contact budget before preparation; every transmission consumes both that
budget and the purpose's disclosure allowance before its first byte. A failed engine remains a
failed engine. A disconnect, quota, challenge, or `Retry-After` cannot authorize another request.
An engine requiring an unmediated call is ineligible. Cancellation fences new transmissions and
requires evidence that owned work stopped; an uncertain terminal state follows Scout recovery
law. Raw queries, query-bearing URLs, provider errors and unkeyed content digests stay out of
general logs, Orb and Loom. Their permitted projections follow Security's restricted-evidence law.

### Search observations and failure meaning

The normalizer returns host-authored attempt/provider/profile references, observation time,
normalizer identity, bounded ordered results, coverage, declared omissions, and separate measured
and provider-reported usage. Each result carries original locator, any derived normalized locator,
rank, plain title/snippet, and provider-reported engine attribution. Normalization preserves query
parameters and path meaning; canonicalization never creates permission to contact the URL.
Provider dates, scores and attribution remain claims, not verified freshness, confidence or truth.
Deduplication retains the contributing identities and ranks. Raw-response and derivation digests
remain restricted local evidence, not public telemetry.

Result count and coverage are independent. Coverage is `no_reported_failure`, `partial`, or
`unknown`; the first means only that the provider reported no failure. Zero results with a failed
or suspended engine is not a clean miss, and an empty error list does not prove every intended
contact completed. Unrecognized engine errors map to a generic attributed failure; translated
provider prose never becomes a stable protocol code. Partial observations are permitted only for
provider-reported engine failures within an otherwise valid admitted exchange. Host authority,
destination/egress, adapter-to-service transport, framing, schema, resource, or cancellation
failure is terminal and cannot be salvaged into successful partial output, even if some results
arrived before the refusal. Invalid required locators refuse the response rather than silently
manufacturing an empty result. A declared top-ten selection is an intentional projection; a byte
ceiling failure is a refusal, not permission to truncate a record.

Generated answers, raw page bodies, images and extra links are outside this profile. The
Scout-owned tool returns attributed data to Context. Fetching a result, retaining its bytes, or
submitting a memory candidate requires the respective owner to admit a separate effect.
[Memory](27-memory.md) keeps candidate intake and explicit promotion; search relevance cannot
grant recall eligibility or instruction authority.

## The first passage

The first designed passage is one unauthenticated static HTTPS GET and network-free extraction:

1. An Agent or admitted application Pattern proposes one exact URL. The host validates its
   principal and Run, admits separate Fetch and Extract grants with their own ceilings, and binds
   the Fetch destination. It selects an eligible static provider, reserves worst-case budget, and
   durably records those exact grants in one Scout effect attempt as `prepared` before I/O.
2. The provider pins and performs one GET with only explicitly bounded, re-gated redirects: no
   subresources, JavaScript, cookies, cache, URL credentials, `.netrc`, ambient proxy, custom
   headers, automatic retry, or rendering. A redirect needs exact current destination and
   disclosure authority, including any required consent; an unlisted redirect refuses by default.
   Describing future redirect gates in the initial review does not authorize unknown targets.
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

### Initial qualification envelope

The `static-public-page@1` envelope below defines a conservative qualification target. Its
numeric limits become usable only with the pinned adapter's conformance evidence; declaring them
does not measure parser safety or document coverage. A limit change creates a changed profile.
Runtime settings may narrow the limits but cannot silently widen a prepared attempt.

| Resource | Ceiling | Enforcing owner |
| --- | --- | --- |
| Contact chain | initial GET plus at most three redirects; one active passage per admitted binding | Scout reservation and destination gate |
| Transfer | 2 MiB encoded body, 4 MiB decoded body, 20:1 cumulative expansion, 64 KiB headers per response; body budgets aggregate across the chain | bounded transport and decoder |
| End-to-end elapsed time | 30 seconds from prepared admission through extraction, including DNS and redirects | host monotonic deadline |
| Extraction | 5 seconds elapsed, 2 seconds CPU, 256 MiB child memory, within the remaining passage deadline | supervisor and OS limits |
| Parse structure | 50,000 elements, depth 128; no external entity, DTD, XInclude, schema or subresource resolution | pinned parser with construction-time limits |
| Serialized return | 256 KiB UTF-8 including attribution | bounded encoder and IPC |
| Retry, paid spend, frontier | zero | Scout admission and transport |

Expired or revoked authority refuses before each new contact. Slots and worst-case budgets are
reserved atomically against both binding and shared host limits; another binding cannot bypass
the aggregate ceiling. Reservations are not released while owned work may still run. Restart reconciles
uncertain reservations with the retained attempt rather than assuming a timeout refunded them.

Parsing and extraction run in a disposable network-denied child, with no acquired sockets,
credentials or workspace authority. The parent supplies bounded decoded bytes and pinned options;
the child cannot fetch, decompress again, load external resources, or invoke an LLM. The host kills
and reaps owned work on timeout/cancellation. OS CPU and memory limits must cover parsing as well
as extraction; post-parse element counts and coroutine timeouts are insufficient. A parser without
construction-time bounds or observable limit failures is ineligible. Silent recovery truncation,
OOM, child crash, limit failure, or unproved cleanup cannot become successful extraction.

One pinned extractor strategy is selected per profile. Heuristic boilerplate removal records its
declared transformations without claiming an exact semantic-loss percentage. Page titles,
bylines, dates, `<base>` and canonical links remain untrusted claims; they cannot replace the
contacted source or trigger another contact. Wire, decoded-body and output identities remain
distinct. Readiness requires representative ordinary and hostile fixtures before any library or
numerical envelope is qualified.

### Native HTTPS transport profile

The native transport receives an exact destination candidate, a host-selected numeric DNS
resolver, an explicit CA file, a remaining monotonic deadline and a mandatory current handoff
gate. None of those values mints an effect grant. It reads no ambient resolver, proxy, credential,
trust-store or TLS key-log configuration.

For a hostname, it asks that resolver for A and AAAA over separate, single TCP contacts, with no
search suffix, UDP fallback, cache or retry. Each response is at most 16 KiB and 64 records; at
most eight CNAME links may be resolved inside the returned message, without another question.
Both families must be complete NOERROR responses for the exact question and agree on the final
name; an empty family requires an enclosing SOA. Every returned destination address passes the
public-address policy before one address is selected. These are observations from the configured
resolver, not DNSSEC proof. Resolver custody remains the authorizer's separate obligation.

The selected numeric peer is checked after the single connect. TLS 1.2 or newer validates the
original hostname against the explicit CA file and certificate SAN, offers HTTP/1.1 only, and
preserves that hostname for SNI and `Host`; an IP literal uses certificate IP identity without
literal-IP SNI. Memory BIOs keep the TLS implementation away from the network socket. Every
actual connect/send, including handshake and read-generated TLS output, crosses the synchronous
gate. Per-connection ceilings are 4 MiB received, 512 KiB sent, 256 KiB handshake input and 256 KiB
handshake/control output, with 16 KiB socket chunks and bounded BIO buffers. Later TLS input shares
the receive ceiling. These limits cannot enlarge the stricter
aggregate HTTP body or passage deadline limits.

The fixed GET carries only `Host`, `Accept`, `Accept-Encoding` and `Connection: close`. Final
success requires status 200, HTTP/1.1, UTF-8 HTML or plain text, and identity or single-member gzip
encoding. Content-length, ordinary chunked and close-delimited bodies are supported. Initial
headers are bounded before the HTTP parser receives them; ambiguous framing, chunk extensions,
trailer fields, informational/upgrade responses, malformed terminators, truncation, trailing data,
unsupported encoding and expansion failures refuse. Body accounting includes chunk framing as
well as encoded payload; decoded bytes are independently bounded. The HTTP response digest names
decrypted HTTP octets, never ciphertext or a claimed network capture.

Redirect observations are resolved only against an exact pre-admitted target list, re-resolved
and re-gated, with loop and aggregate-budget checks. Relative references whose empty path
segments would be changed by the URI resolver refuse. Transport EOF is required before a response
becomes complete. Fetch and extraction share the remaining passage deadline; cancellation closes
the socket and awaits extraction containment. A cleanup uncertainty cannot become a successful
page result. These mechanisms remain unexposed until durable attempts, current authority and the
hosting workflow are assembled and qualified together.

### Native text extraction profile

The first native extractor uses a fixed standard-library worker for strict UTF-8 `text/html`
and `text/plain`. It accepts decoded bytes, not a locator, executable, parser plugin, credential,
or network handle. HTML is projected to text without a document tree: element and nesting limits
apply during parsing. Head, script, style, template, SVG, MathML and comment content is omitted;
attributes and source-supplied base/canonical links confer no authority. A bare HTML5 doctype is
inert; external or internal DTDs, processing instructions and other declarations refuse. The
versioned strategy declares its whitespace and structural transformations. This is neither a
browser's rendering nor article extraction, factual verification or prompt-injection removal.
Malformed input outside that strategy refuses rather than being silently repaired into success.

The private child protocol has one bounded header, an exact body length and EOF. Decoded input is
at most 4 MiB. One UTF-8 JSON response is at most 240 KiB, leaving room within the passage's
256 KiB return ceiling for host-authored attribution; the passage must still count its complete
serialized return. Invalid encoding, trailing input, unsupported media, output overflow, child
failure and malformed returns are terminal refusals. Errors use closed codes, never source text.
The parent verifies returned structure and computes decoded-input and serialized-output digests;
neither is a network-wire digest or permission to retain the material.

The Linux host supplies an explicitly reviewed Bubblewrap executable, dedicated Python runtime
and finite loader/library closure. The fixed worker receives an empty filesystem root with those
read-only runtime mounts, fresh user, PID, network, IPC and UTS namespaces, cleared environment,
dropped capabilities and closed unrelated descriptors. It receives no checkout, home, host proc
mount, credentials or writable host directory. Namespace creation and disabling nested user
namespaces are mandatory; there is no bare-process fallback. The assembled mount root is
read-only. CPU and virtual address space are bounded before acquired input is processed; core
dumps are disabled and the fixed worker cannot fork or create threads. `RLIMIT_AS` is an
address-space ceiling, not an RSS measurement or cgroup memory guarantee. The supervisor bounds input/output, enforces the five-second
wall deadline and separately bounds kill/reap cleanup; unknown cleanup cannot produce success.

Qualification belongs to the actual host/runtime/profile combination. Tests of command assembly
or substituted processes establish only those contracts. A live qualification must demonstrate
network and host-file denial, descriptor/environment isolation, limit failures and termination of
namespace descendants, including a new-session descendant. Availability of `bwrap`, an exit code,
or a passing extraction fixture alone does not establish containment. This extractor is a local
mechanism: Fetch/Extract grants, egress decisions, durable acquisition attempts, workflow binding
and artifact custody remain separately owned prerequisites to a Scout passage.

### Native RSS 2.0 extraction profile

The `scout-rss-extract@1` profile shares the fixed worker's physical containment and
supervisor with text extraction; it has a separate request and structured return. The existing
static text profile still accepts only HTML/plain text. Its two-field private header must refuse
XML. RSS needs the exact additional profile identity and one of `text/xml`, `application/xml`, or
`application/rss+xml`; a media label alone cannot select it. Neither mechanism admits Fetch,
recurring watching, custody or any item contact.

The first profile accepts strict UTF-8 RSS 2.0, one unnamespaced `rss` root and one `channel`.
A declaration, when present, must name XML 1.0 and UTF-8. It retains channel title, locator and
summary, and at most 100 item observations with title, original locator, summary and optional
publisher date/identifier. Channel title/locator/summary are required; each item needs a locator
and nonempty title or projected summary. Duplicate selected fields, nested XML inside those
fields, non-whitespace text in structural RSS/channel/item containers, malformed/truncated XML
and missing required values refuse the complete result.
Namespace extensions and unselected elements/attributes are omitted with declared loss and an
omitted-element count; they cannot impersonate selected fields. Publisher dates and identifiers
remain claims, never verified freshness, global identity or a deduplication authority.

| Resource | RSS ceiling |
| --- | --- |
| Decoded UTF-8 input | 1 MiB |
| Element count / depth / items | 10,000 / 64 / 100 |
| Title / locator / summary | 1,024 / 4,096 / 8,192 UTF-8 bytes per field |
| Publisher date / identifier | 128 / 1,024 UTF-8 bytes per field |
| Serialized return | 240 KiB, within the enclosing passage's remaining return budget |
| Child wall / CPU / address space | 5 seconds / 2 seconds / 256 MiB, no wider than static extraction |

A field or output ceiling refuses rather than truncating items. XML-decoded scalar construction
is bounded before trimming or description projection, even if that later transformation would
shorten the field; the projected value is checked again. XML whitespace surrounding a
selected scalar is removed without rewriting locator paths or queries. RSS descriptions containing
escaped HTML or CDATA use the fixed HTML text strategy inside the same child; source instructions
remain data. Description attributes are omitted after control checks; numeric references are
checked before HTML5 replacement can erase a forbidden control. Selected locators are independently checked by the parent against Scout's existing
pure HTTPS destination-syntax contract. That validation performs no DNS or contact and grants
neither; each later contact needs fresh current authority.

Parsing uses the runtime's Expat with reparse deferral enabled and version at least 2.6.0, under
the same pre-input hard process limits. DTDs, entity declarations, external entities and processing
instructions refuse before they can acquire authority or resources. XML declarations are handled
separately; encoding declarations cannot broaden strict UTF-8. Raw and entity-decoded text obey
the existing control-character policy, including omitted material. Construction-time element/depth
and input bounds apply to omitted material too; selected fields are bounded incrementally. No
DOM, external resource loader, browser or Core XML parser substitutes for the isolated child.

Qualification must join ordinary and hostile RSS behavior to the exact shared worker, supervisor,
interpreter and containment closure. A changed worker requires fresh evidence for existing text
profiles as well; an earlier static receipt cannot qualify RSS. Network acquisition and native
workflow admission remain subsequent, separately proved boundaries.

## Destination and data boundary

Every external acquisition URL, redirect, and new connection is independently authorized: canonical HTTPS
scheme, hostname, port, and origin only; no userinfo or unsupported scheme. Resolution runs
without ambient proxy or credentials and rejects mixed or forbidden addresses (loopback, private,
link-local, multicast, unspecified, and metadata). The approved address is pinned through the
connection; connected peer, TLS certificate, SNI, and `Host` must match. Redirects are manual,
bounded, loop-checked, and re-gated. An HTTP client or crawler SDK alone cannot establish this
SSRF/DNS-rebinding boundary.

### Destination preflight

The bounded `public-https-destination@1` preflight performs no resolution or contact. It accepts
at most 4 KiB of ASCII URL text, HTTPS on port 443 only, a canonical dotted DNS hostname or
canonical public IP literal, and no userinfo, fragment, whitespace, control character, backslash,
encoded authority, or malformed percent escape. DNS case is normalized; an explicit `:443` may
be omitted. Path/query bytes, including an empty query delimiter, retain their meaning. Unicode
host conversion, alternate numeric address spellings, scoped IPv6 and custom ports require a
separately reviewed profile rather than permissive parser repair.

A second pure check classifies a supplied complete, bounded A/AAAA answer set for that exact
hostname. Empty, malformed, duplicate-overflow, forbidden or mixed sets refuse; IP literals must
match the supplied address exactly. The conservative policy excludes special-purpose IPv4 ranges
and allows ordinary IPv6 global unicast only, excluding special-purpose and transition ranges.
The policy is explicit and versioned rather than inherited from changing standard-library
`is_global` tables. Positive facts remain an immutable candidate, not a grant or evidence that a
resolver actually returned them. The future trusted resolver must establish completeness and
freshness; transport must still pin and verify the actual peer, TLS identity, redirects, authority
and budget. A caller-constructed candidate cannot bypass those gates.

An acquisition receipt names the effect, principal/Run, provider/version, policy, locator and
redirects, destination evidence, time, disposition, media/size, usage, and raw digest. It proves
an attempted effect, not a correct response. Responses and derivations remain attributed data:

```text
locator != response != derived statement != trusted fact
acquired != admitted != understood != promoted
```

They are never instructions, code, policy, or truth. Interpretation belongs to
[Drift (34)](34-evaluation.md) or the consuming Composition.

## Custody and stronger tracks

Acquired bytes remain ephemeral until their custody owner verifies digest, media type, size,
classification, retention, retrieval authority, and storage and returns a retrievable
`ArtifactRef`. A digest or receipt alone is not an artifact, and an arriving download enters
bounded quarantine rather than creating a workspace or artifact. Render, Interact, Credential Use,
Session Custody, Screenshot, and Download remain Designed. JavaScript or a challenge produces
refusal or `human_required`, never a browser.

Any future renderer needs a finite destination/egress grant and isolation from Core peers, host
paths, databases, control sockets, wallets, and unrelated secrets. Credentials are opaque,
principal- and origin-scoped references outside prompts and telemetry. A browser-bearing
Soulstone may not join the shared `lychd.pod`; it needs a dedicated rootless containment and
network zone whose only target egress crosses the Scout gate.

## Qualification evidence

The following are acceptance obligations, not existing tests or runtime receipts. Each profile
must bind its actual finite request, response, parser, time, concurrency and disclosure ceilings;
missing, unlimited, negative or nonfinite values refuse admission. Search additionally fixes
query/locator/title/snippet limits and a per-engine contact plan before qualification.

| Case | Required observation |
| --- | --- |
| Wrong effect, stale binding, forged provenance, mutable registration | refusal before contact; no raw provider tool is exposed |
| Query bangs, preferences, extra parameters, inherited engines, service initialization | no unadmitted recipient or auxiliary request |
| Disconnect, redirect, timeout, quota, challenge, cancellation | no hidden retransmission, provider switch, or stronger effect; uncertain work is not reported settled |
| Partial engine failure, suspension, empty result, missing coverage | distinct attributed observations; no exhaustive-search claim |
| Valid result JSON after a host-denied auxiliary request | terminal refusal, never successful partial output |
| DNS rebinding, mixed public/private answers, peer mismatch, redirect to metadata | no application bytes reach the forbidden destination |
| Compression bomb, malformed framing/JSON, invalid locator, limit and limit-plus-one input | deterministic bounded refusal; no salvaged partial success |
| Deep/wide markup, expensive parsing, OOM, external entities and resources | Core survives; bounded child termination; no unauthorized network or file read |
| Prompt injection, forged receipts, canonical links and provider error text | unchanged authority and host attribution; no follow-up contact, automatic custody or memory promotion |
| Crash between preparation, transmission, extraction and settlement | retained identity and unknown outcome; no blind replay or early budget refund |
| Changed image, parser, engine, effective config or driver | old qualification cannot authorize a new binding |

### Upstream comparisons

These primary references informed the design review on 12 October 2026; they do not qualify a
dependency or deployment. Recheck the exact selected revision before implementation.

- **SearXNG:** [JSON API](https://docs.searxng.org/dev/search_api.html),
  [query syntax](https://docs.searxng.org/user/search-syntax.html) and
  [engine settings](https://docs.searxng.org/admin/settings/settings_engines.html) support the
  separate search adapter, but default-disabled engines and query routing are not authorization.
  At [ad46ebd7d](https://github.com/searxng/searxng/blob/ad46ebd7d/searx/network/network.py#L249-L279),
  the first connection-error branch permits another client request even with zero configured
  retries. This is evidence of a permitted retry path, not proof that every such error retransmits
  application bytes. Qualification must observe and constrain that path.
- **Tavily:** its [Search API](https://docs.tavily.com/documentation/api-reference/endpoint/search)
  demonstrates optional generated answers, raw content, automatic parameter selection and usage.
  A future private Portal must close those choices explicitly; the endpoint name alone does not
  establish its effects or cost. It remains outside the first-party provider set.
- **Trafilatura and Readability:** [Trafilatura's extraction source](https://trafilatura.readthedocs.io/en/latest/_modules/trafilatura/core.html)
  checks output tree size after parsing/extraction; [Readability](https://github.com/mozilla/readability)
  consumes an already-built DOM and does not sanitize returned HTML. Their article-selection
  mechanisms are comparison candidates, not parser containment. Neither extractor is selected
  without coverage and resource evidence; return plain attributed text through the same boundary.
- **Crawl4AI and Firecrawl:** [Crawl4AI configuration](https://docs.crawl4ai.com/core/browser-crawler-config/)
  exposes browser powers wider than the selected passage; [Firecrawl self-hosting](https://docs.firecrawl.dev/contributing/self-host)
  introduces a broader service stack. Keep the existing renderer candidate and deferred comparison
  until a demonstrated static-coverage gap justifies their operating and containment cost.

## Delivery Boundary

The native public-page profile implements bounded Fetch and Extract through opt-in
`bridge_chat@4`, with authenticated declaration, native consent and durable attempt accounting.
It is distinct from the general provider, Search, Crawl and Render surfaces designed above.
[State of Work](../state-of-the-work.md#scout-web-acquisition) owns its current evidence envelope:
separately qualified network/extraction mechanisms and controlled workflow/PostgreSQL checks do
not establish a deployed application-to-model passage or arbitrary host compatibility.

The pure `public-https-destination@1` checks remain preflight facts; only the admitted transport
can establish connected-peer and transmission evidence. A locator, model declaration, generic
runtime test or `ArtifactRef` cannot supply missing authority or custody.

No Scout-owned general provider contribution, effect-scoped Agent tool, robots/rate scheduler,
browser, download quarantine or Reliquary is delivered by that profile. Search mediation and
renderer isolation require their own qualification; the native path cannot grant their effects
or make the shared Pod an acceptable browser boundary. The
[Scout topic](../sepulcher/extensions/scout.md#public-page-answers) owns configuration and operation.

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
