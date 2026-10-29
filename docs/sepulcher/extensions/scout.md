---
title: Scout
icon: material/navigation-variant-outline
---

# :material-navigation-variant-outline: Scout

An Agent proposes one URL. Before contact, the host must decide which acquisition effect,
destination, identity, and budget are admitted. **Scout** carries that exact attempt through
bounded acquisition and attributed return. The response remains external material; the consuming
Composition decides what it means and whether it serves the work.

> _Bring back the voice, and the trail that led you to it._

Scout follows [Webcrawler](../../adr/30-webcrawler.md).
[State](../../state-of-the-work.md#scout-web-acquisition) distinguishes the verified mechanisms
and opt-in public-page workflow from Search, Crawl and Render work that remains unfinished.

## The first passage

The first implementable passage is one static public HTTPS page:

1. **Prepare.** An Agent proposes one exact URL. The Host binds it to the canonical Run, verified
   principal, origin policy, and consent where required. It admits separate Fetch and Extract
   grants with their own ceilings, reserves worst-case budget, and durably records those grants
   in one Scout effect attempt as `prepared` before network I/O.
2. **Pass.** A static adapter authorizes and pins the destination for one bounded GET, repeating
   the gate for every redirect. It uses no ambient proxy, credentials, cookies, subresources,
   JavaScript, or automatic retry. A network-free extractor accepts bounded HTML, XHTML, or plain
   text and returns attributed, fenced material tied to raw and output digests.
3. **Settle.** A second durable transaction records usage and terminal disposition. Raw bytes are
   released after extraction unless a separate custody service admits them.

The passage must resist SSRF and destination rebinding, treat every response as hostile, and
enforce hard network, parser, output, concurrency, and cost ceilings. After a crash, a stranded
bounded-call Scout effect attempt is `unknown_after_crash` unless independent evidence reconciles
it. A missing terminal record never authorizes a blind retry.

Needing JavaScript is a typed static-passage outcome, not permission to invoke Crawl4AI. The
caller must request and receive new Fetch, Render, and Extract effect grants for that exact locator and
provider profile.

## Ten tracks through the wild

To decide what a request actually authorizes, separate the effects often hidden behind the word
“browser.” **Search** discovers locators. A subsequent **Fetch** performs one bounded network
read, and **Extract** transforms the acquired bytes without a network. **Crawl** adds management
of a finite frontier; **Render** executes hostile site code. **Interact** goes further by
clicking, typing, submitting, or uploading.

Identity and retained state have their own effects: **Credential Use** presents one scoped
secret reference, and **Session Custody** owns cookies and browser state. **Screenshot** requests
pixels; **Download** transfers a bounded payload into quarantine. Only the separate custody-owner
effect, Artifact Admission, can validate and retain exact bytes. Downloading therefore supplies
neither admission nor the trust or understanding that durable storage also cannot establish.

Each Scout track needs its own host-owned `ScoutEffectGrant` and budget. A redirect, JavaScript
requirement, CAPTCHA, login, payment challenge, quota response, or failure is a result, never
permission to retry, change provider, present identity, spend, or open a stronger track. Provider
selection cannot widen the effect grant.

## Attempt layers

For one bounded synchronous call, Scout owns an effect attempt and records `prepared` durably
before any I/O. The implementation determines the additional execution authority: an
Animator-backed implementation holds a scoped `CallGrant`, while a native host-owned adapter
pins its exact Scout provider/adapter binding and uses no Dispatcher lease. Neither immediate
call creates a `ServiceJobAttempt@1`.

If the process crashes without independent terminal evidence, Scout records the domain
disposition `unknown_after_crash`. Longer asynchronous crawl or render work uses `JobGrant`
and keeps a Scout domain job over Core's
[`ServiceJobAttempt@1`](../../adr/14-workers.md#service-job-attempts). There the same domain
uncertainty maps to `INDETERMINATE`; recovery must reconcile the same capability-backed execution
binding rather than create a replacement attempt.

## Contact does not become truth

A result needs an account of both contact and transformation before a reader can judge it.
Following [Oculus](oculus.md), Scout records the attempted acquisition as an **effect receipt**,
the source response as a **bounded observation**, and each transformation as a **derivation**
that identifies its parentage and loss. **Interpretation** comes afterward: applying declared
criteria belongs to [Drift](drift/trials.md) or the consuming Composition.

These records also leave custody explicit. A digest supplies neither proof nor custody, and an
`ArtifactRef` remains metadata until a service admits retrievable bytes under the
[artifact-custody boundary](../../state-of-the-work.md#artifact-reference-contract).

## Sources are senses, not applications

A site, feed, or API is a source surface. Its adapter belongs beneath Scout; the consuming
[Composition](../../compositions/index.md) owns why the observation matters, the criteria applied
to it, and any consequence. Scout may observe a listing. It cannot decide that the listing suits a
person or authorize a purchase.

An admitted application Pattern may therefore place a Scout effect for an exact locator it has
judged eligible for its purpose. That placement does not move Fetch, Download, destination, retry,
or acquisition-receipt semantics into the application. Conversely, Scout's destination grant says
only that contact is allowed; it cannot make the source eligible for an application. Downloaded
bytes enter quarantine, and only the custody owner may validate and return a durable artifact
reference.

A saved Search, Watch, Source Profile, crawl schedule, or deduplicator remains Scout mechanism
until it gains an operator-visible purpose and lifecycle. **Hunter** remains [Shadow's adversarial
Posture](shadow/hunter.md), not a web-acquisition role.

## The chosen road

The first-party path is local and replaceable:

```text
SearXNG Search -> attributed locator
                       |
                       +-> native static Fetch -> offline Extract
                       |
                       +-> newly granted Crawl4AI Fetch + Render + Extract
```

- **SearXNG** is the selected Search Soulstone. It returns locators and snippets; it does not
  contact a result on the Agent's behalf under a Fetch effect grant.
- **Native static Fetch + Extract** is the ordinary passage for a public page that needs no
  JavaScript.
- **Crawl4AI** is the experimental renderer candidate for one exact public HTTPS URL. Despite its
  name, the initial profile receives no Scout Crawl frontier and exposes no arbitrary browser,
  JavaScript, MCP, credentials, session, screenshot, download, or LLM surface.
- **Firecrawl** is deferred, not installed beside Crawl4AI for speculative redundancy. It returns
  to comparison only if it demonstrates a material advantage under the same grants, isolation,
  evidence, and operating budget.
- **Browserless** is not a parallel first-party backend. Raw CDP, Playwright, function execution,
  and download surfaces are wider than the selected renderer passage; it returns only for a proved
  gap, not provider-count symmetry.

There is no first-party paid web-acquisition Portal adapter. A Magus may write a private extension
for Tavily, hosted Firecrawl or Browserless, or another remote provider, accepting its
compatibility, retention, spend, and policy boundary, but it must still enter through Scout. A
Portal declaration or Dispatcher capability grant cannot authorize a query or page contact, and provider
failure never triggers a cloud fallback.

Here **native adapter** means the LychD-owned Rune, probe, narrow request/response translation,
normalization, and conformance tests around a separate service. It does not mean vendoring the
SearXNG engine catalogue or a crawler/browser implementation into Core. The full provider and
mechanism policy belongs to [ADR 30](../../adr/30-webcrawler.md#first-party-mechanism-policy).

For a known source, first compare its existing static page or advertised feed with the cost of
a search service or browser. The [source acquisition study](#source-acquisition-study) traces the
Bazoš page/RSS premise and the separate qualification needed for each source profile. The separate
`scout-rss-extract@1` mechanism projects strict RSS 2.0 in the fixed child;
[State](../../state-of-the-work.md#scout-web-acquisition) owns its evidence boundary. The native
feed source contract below does not establish installed operation or recurring listing watching.

The [first Search profile](../../adr/30-webcrawler.md#searxng-search-contract) is deliberately
bounded to one qualified engine and one page. Self-hosting does not keep the query local: the
engine receives an external disclosure. Scout must mediate those requests before transmission,
including any auxiliary contact; installing SearXNG and setting its retry count is insufficient.
An engine failure remains visible alongside any results, and zero results never claims the web
has no answer. No compliant engine profile or transport integration ships yet.

For implementation, start with the [static qualification envelope](../../adr/30-webcrawler.md#initial-qualification-envelope)
and [adversarial acceptance cases](../../adr/30-webcrawler.md#qualification-evidence). The
[native extractor](../../adr/30-webcrawler.md#native-text-extraction-profile) accepts already
acquired UTF-8 HTML or plain text in a network-denied child. It returns an ephemeral text
projection with declared transformations, not browser rendering, article understanding or removal
of source-authored instructions. Its [host qualification procedure](https://github.com/hexanomicon/lychd/blob/main/CONTRIBUTING.md#quality-checks)
uses an explicit runtime profile and synthetic fixtures. Passing it grants no Fetch, custody or
workflow authority. Search and JavaScript rendering retain their separate admission and isolation
gates.

The [native HTTPS transport](../../adr/30-webcrawler.md#native-https-transport-profile) has a
separate isolated-network qualification: real DNS and TLS fixtures lead into the extractor,
while certificate, destination, framing and current-handoff refusals remain visible. It accepts
ordinary HTTP/1.1 HTML/plain-text responses with identity or gzip encoding. Chunk extensions,
trailers and unlisted redirects refuse. This mechanism proof uses a synthetic gate; durable
attempts and current operator authority have their own PostgreSQL and workflow checks. Neither
receipt alone proves a deployed application, a selected model or arbitrary host compatibility.

## Public-page answers

The opt-in `bridge_chat@4` casting prepares a native review, waits for your decision, acquires one
page and answers with one exact local chat capability. Its Bridge command is:

```text
/read-public https://example.com/page
What does this page claim?
```

Sending this command asserts that the complete locator, including its path and query, is public.
The assertion requires the actual authenticated local operator and current Scout classification
policy. It is not proof of publicness. The review identifies the URL, resolver and its declared
custody, DNS/TLS disclosures, resource ceilings, local model and answer retention before contact.
Approval grants neither retries nor additional URLs.

Select revision 4 in `lychd.toml` only with PostgreSQL and an independently qualified extraction
runtime. These example paths and capability names must be replaced with your reviewed inventory:

```toml
[weaver.bridge]
revision = "4"
capability_key = "my-runtime:chat:my-local-model"

[weaver.bridge.scout]
binding_id = "public-page-local"
policy_revision = 1
revocation_generation = 0
resolver_address = "127.0.0.1"
resolver_port = 53
resolver_custody_statement = "This operator-owned resolver forwards the declared public hostname to its configured upstream."
ca_file = "/etc/ssl/certs/ca-certificates.crt"
bwrap = "/usr/bin/bwrap"
python_root = "/opt/scout-python"
libraries = [
  "/lib64/ld-linux-x86-64.so.2", "/lib64/libc.so.6", "/lib64/libdl.so.2",
  "/lib64/libgcc_s.so.1", "/lib64/libm.so.6", "/lib64/libpthread.so.0",
  "/lib64/librt.so.1", "/lib64/libutil.so.1",
]
max_context_chars = 16000
review_ttl_seconds = 300

[weaver.bridge.scout.allowance]
connects = 3
transmissions = 512
wire_bytes = 1048576

[weaver.bridge.scout.budget_limits.host]
connects = 30
transmissions = 5120
wire_bytes = 10485760

[weaver.bridge.scout.budget_limits.binding]
connects = 15
transmissions = 2560
wire_bytes = 5242880
```

The resolver address must be numeric; its reachable TCP listener and upstream custody are operator
configuration. The example does not start a resolver or qualify those paths. The dedicated Python
tree must contain no operator material. Runtime and library qualification follows the maintained
Linux proof procedure in the contribution guide.

HTTP and workers share one Scout authority and cancellation fence, so either entry path must
honor the same attempt and budget. Before I/O, each attempt reserves worst-case outbound
counters; only observed completion lets it settle actual usage. One binding admits one active
acquisition. Its budgets are cumulative: renaming the binding or restarting the process cannot
reset them.

An unknown crash outcome keeps both its reservation and its slot. This profile supplies no
automatic reconciliation or retry. If the configured budget changes, it refuses against existing
budget rows rather than discard the accounting that still governs those attempts.

Acquired bytes enter the selected local model as bounded, attributed, untrusted data. Token
counting and inference both require current authority. There are no model tools, remote fallback,
settled-history replay or automatic redirects. The ordinary answer is retained and may quote the
page; raw acquisition and its injected envelope are not saved in Graph state or model history.
Lost transient material cannot be reconstructed from a receipt or silently fetched again.

Revision 4 becomes the selected Bridge profile, so other message forms refuse there. Removing
the selector restores the default for new admissions; retained Runs keep their original revision.
Restart replaces the authentication generation, so prior prepared work cannot acquire fresh
authority merely by restoring its records. Loom displays the registered score and its activation;
it does not edit this casting or activate Search, Crawl or Render.

## Finite Scavenger feed observation

The source contract selects Scavenger revision `3`, `scavenger.observe_market@2` and
`bazos-pc-title-link@1`: one model-free observation of
`https://www.bazos.sk/rss.php?rub=pc`. The [application contract](../../compositions/scavenger/market.md#finite-feed-observation)
owns the complete seed, retained field and recovery semantics. This operation description is not
a delivery receipt; [State](../../state-of-the-work.md#scout-web-acquisition) owns qualification.

Opt in through `lychd.toml` with `[weaver.scavenger]` and `revision = "3"`. Its required
`[weaver.scavenger.scout]` value is an exact `ScoutFeedProfile`: `provider_id = "native-static@1"`,
`profile = "rss-public-feed@1"`, `binding_id`, `policy_revision`, `revocation_generation`,
`resolver_address`, `resolver_port`, `resolver_custody_statement`, `ca_file`, `bwrap`,
`python_root`, `libraries`, `allowance`, `budget_limits` and `review_ttl_seconds`.
Use the reviewed absolute runtime/library paths, numeric resolver and nested host/binding budget
shapes illustrated in the public-page example above. This feed profile has no `capability_key`
or `max_context_chars`. Configuration syntax does not establish runtime readiness.

Only one Scout binding may be selected: `weaver.bridge.scout` at Bridge revision 4 cannot coexist
with `weaver.scavenger`. The initial profile requires a fresh profile database; existing page
budget rows refuse a page/feed switch without mutation. Omitting `weaver.scavenger` disables new
observation admission. Removing configuration grants no migration, cleanup or accounting reset.

Use the Altar's `/scavenger` application view with the authenticated same-host operator.
Supply the complete bounded `CampaignSeed@1` through its seed form/API, including explicit empty
arrays and explicit unknown budget/region where needed. The application owns the complete seed
and request body; Run/Graph facts and generic history carry references, never a copied seed.
Neither seed nor feed field enters a model, Bridge history or a model prompt. The `Watch` seed
ceiling grants no cadence, ranking, seller contact, item fetch or purchase.

For direct API operation, the exact request is `ObserveMarketRequest` with `request_id`, `seed`
and `initial_filter`; the filter is `{"revision":"literal-casefold@1","query":""}` for all rows.
Retain that request identity: identical replay resolves the same admission; changed content under
that identity refuses. The source fixes the locator and execution profile; neither comes from
request text. The protected application routes are:

| Method | Path | Operation |
| --- | --- | --- |
| GET | `/api/v1/scavenger` | Current configured state and retained field |
| POST | `/api/v1/scavenger/observations` | Reserve and admit the complete request |
| GET | `/api/v1/scavenger/observations/{admission_id}` | Read the application document |
| GET | `/api/v1/scavenger/observations/{admission_id}/consent` | Project its exact current Core consent |
| POST | `/api/v1/scavenger/observations/{admission_id}/view` | Apply a local `LiteralFilter` |
| POST | `/api/v1/scavenger/observations/{admission_id}/delete` | Delete terminal controlled payload |

Admission requires `runs:submit`; reads and local filtering require `altar:read`; deletion
requires `runs:cancel`. Each also rechecks the current application owner and credential authority.
Use the normal authentication and CSRF boundary for mutations; UUIDs and digests are not grants.
Review the exact Core consent before contact. Use its `consent_id` in
`POST /api/v1/bridge/consents/{consent_id}/decision`; submit `verdict` and the presented
`review_binding_digest`, requiring
`runs:approve` and current review authority. The digest must match for approval or denial.
The review binds the fixed source, disclosures, consumer, ceilings and expiry; consent is not a
reusable Fetch grant. Current network, CONSUME and application-adoption authority still apply.

The retained whole field includes every returned title/link occurrence, in source order,
including unmatched, duplicate and missing-title rows. Inspect source/time/coverage, omissions
and total/visible/unmatched/duplicate/missing counts. Item links remain inert displayed data.
The application field retains only admitted titles, links and necessary attribution; raw feed,
channel and summary content are excluded from that retained field. A case-folded literal substring filter derives visible ordinals over the same
field digest. An empty query shows all rows. Filtering performs no source contact and changes no field.

Cancel pending work explicitly through `POST /api/v1/bridge/runs/{run_id}/cancel` and inspect its
settlement. Cancellation and deletion are separate operations. Terminal deletion submits the
exact `request_digest` and `observation_digest` (explicit `null` when absent) to the delete route.
It removes application seed and field payload atomically and retains a content-free tombstone
plus necessary execution/Scout receipts. It does not erase independent contact metadata or
backups. A deleted observation is distinct from an observed empty field; replay cannot restore it.

Recovery begins with what the retained records actually establish. Unknown custody/disposition
stays unknown and blocks terminal-only deletion. Receipt digests cannot reconstruct a lost
transient field, and loss cannot authorize a silent refetch. When the field is confirmed committed,
fresh authority permits reading and re-filtering it. When only the acknowledgement is ambiguous,
reconciliation stays with that same identity.

Deleting a terminal field reopens the application slot, but preserves spent budgets, unknown
reservations, and an issued claim. Replacing it requires a visible delete, a fresh request, and
fresh consent. This source contract promises no automatic retry, restart recovery acquisition,
or budget reset.

## The laws of the road

- **Pin before connecting.** Reauthorize every connection and redirect; forbidden or mixed DNS,
  peer mismatch, rebinding, and ambient proxies fail closed.
- **External material remains external.** Queries are classified egress, and returned content may
  contain injection, secrets, falsehood, or hostile structure. It enters Context only as
  attributed, fenced data, never instruction or tool authority.
- **Refusal remains refusal.** Robots policy, site terms, authentication, and law are distinct. A
  denial or challenge returns a typed outcome; Scout does not evade it or rotate identity.
- **Credentials and browsers stay isolated.** Secrets remain opaque and scoped outside prompts
  and ordinary telemetry. Any future renderer is disposable and separated from Core peers, Host
  paths, databases, control sockets, wallets, and unrelated secrets. It does not join the shared
  `lychd.pod`.
- **Bytes enter quarantine before custody.** Arrival grants no workspace, execution, or durable
  artifact name; admission must establish provenance, classification, retention, and retrieval.
- **Spend requires authority.** Reserve bounded resources and spend; paid providers and price
  challenges grant no payment authority.

The full destination checks, receipt fields, parser ceilings, and transition mechanics remain in
[ADR 30](../../adr/30-webcrawler.md).

## The next gate

Scout acquires and attributes. [Prism](prism/index.md) may act on visual bytes only after custody admits
them. [Smith](smith.md) may propose a candidate from admitted sources. None appoints the next:

```text
acquired ≠ admitted ≠ understood ≠ trusted ≠ promoted
```

## Source acquisition study {#source-acquisition-study}

**Maturity: candidate study, reviewed 18 October 2026.** This study selects the next experiment;
the separately qualified RSS extractor is recorded in State. Native feed acquisition/workflow,
monitoring and standing authority remain outside this study.
Scout’s operating contract above, [ADR 30](../../adr/30-webcrawler.md) and
[State](../../state-of-the-work.md#scout-web-acquisition) retain those boundaries.

### Choose the source surface before adding a service

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

### What the live source established

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

### What other projects contribute

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

### Feed experiment: one feed, one attributed digest {#next-vertical-slice-one-feed-one-attributed-digest}

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


### SearXNG transport cut — 18 October 2026 {#searxng-transport-cut}

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


### Full service fixture: context must cross the dispatcher

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
