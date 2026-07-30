---
title: Scout
icon: material/navigation-variant-outline
---

# :material-navigation-variant-outline: Scout

> _A Scout may bring a voice from beyond the Circle. It may not grant that voice the throne._

**Scout** is LychD's web-discovery and acquisition Extension Domain. It acquires external material
under explicit authority and limits; truth, permission, interpretation, and application purpose
remain elsewhere.

**Delivery: Designed, not delivered.** [State of
Work](../../state-of-the-work.md#scout-web-acquisition) records the exact boundary;
[ADR 30](../../adr/30-webcrawler.md) owns the acquisition law and protocol.

## Nine tracks through the wild

Scout separates effects often hidden behind the word “browser.” **Search** discovers locators;
**Fetch** performs one bounded network read; **Extract** transforms acquired bytes without a
network; and **Crawl** manages a finite frontier. **Render** executes hostile site code;
**Interact** clicks, types, submits, or uploads. **Credential Use** presents one scoped secret
reference; **Session Custody** owns cookies and browser state; **Screenshot** requests pixels.

Each track needs its own grant and budget. A redirect, JavaScript requirement, CAPTCHA, login,
payment challenge, quota response, or failure is a result, never permission to retry, change
provider, present identity, spend, or open a stronger track. Provider selection cannot widen the
grant.

## Sources are senses, not applications

A site, feed, or API is a source surface. Its adapter belongs beneath Scout; the consuming
[Composition](../../compositions/index.md) owns why the observation matters, the criteria applied
to it, and any consequence. Scout may observe a listing. It cannot decide that the listing suits a
person or authorize a purchase.

A saved Search, Watch, Source Profile, crawl schedule, or deduplicator remains Scout mechanism
until it gains an operator-visible purpose and lifecycle. **Hunter** remains [Shadow's adversarial
Posture](shadow/hunter.md), not a web-acquisition role.

## The first passage

The first implementable passage is one static public HTTPS page:

1. **Prepare.** An Agent proposes one exact URL. The Host binds it to the canonical Run, verified
   principal, origin policy, consent where required, and worst-case budget, then durably records
   the prepared attempt before network I/O.
2. **Pass.** A static adapter authorizes and pins the destination for one bounded GET, repeating
   the gate for every redirect. It uses no ambient proxy, credentials, cookies, subresources,
   JavaScript, or automatic retry. A network-free extractor accepts bounded HTML, XHTML, or plain
   text and returns attributed, fenced material tied to raw and output digests.
3. **Settle.** A second durable transaction records usage and terminal disposition. Raw bytes are
   released after extraction unless a separate custody service admits them.

The passage must resist SSRF and destination rebinding, treat every response as hostile, and
enforce hard network, parser, output, concurrency, and cost ceilings. After a crash, a stranded
attempt is `unknown_after_crash` unless independent evidence reconciles it. A missing terminal
record never authorizes a blind retry.

## Contact does not become truth

Following [Oculus](oculus.md), Scout records an attempted acquisition as an **effect receipt**, one
source response as a **bounded observation**, and each transformation as a **derivation** with
parentage and loss. **Interpretation** applies declared criteria and belongs to
[Riddle](riddle/trials.md) or the consuming Composition. A digest is neither proof nor custody, and
an `ArtifactRef` remains metadata until a service has admitted retrievable bytes under the
[artifact-custody boundary](../../state-of-the-work.md#artifact-reference-contract).

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
  paths, databases, control sockets, wallets, and unrelated secrets.
- **Bytes enter quarantine before custody.** Arrival grants no workspace, execution, or durable
  artifact name; admission must establish provenance, classification, retention, and retrieval.
- **Spend requires authority.** Reserve bounded resources and spend; paid providers and price
  challenges grant no payment authority.

The full destination checks, receipt fields, parser ceilings, and transition mechanics remain in
[ADR 30](../../adr/30-webcrawler.md).

## The next gate

Scout acquires and attributes. [Prism](prism.md) may act on visual bytes only after custody admits
them. [Smith](smith.md) may propose a candidate from admitted sources. None appoints the next:

```text
acquired ≠ admitted ≠ understood ≠ trusted ≠ promoted
```
