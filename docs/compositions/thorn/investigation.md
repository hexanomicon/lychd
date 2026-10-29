---
title: Follow the Campaign
icon: material/map-marker-path
---

# Follow the campaign

One defender receives a lure. Another records an access attempt. A third discovers unusual use
of an account. Thorn should help them determine which encounters belong together, what the
evidence establishes, and which observation would resolve the next useful question.

This is the investigative journey within the [Thorn candidate](index.md). During an attack,
admitted protection proceeds without waiting for this inquiry. A separately authorized assessment
can start with a security question instead of an incident; its target, methods, possible effects,
and stopping conditions enter the same case scope.

## Open a lead with an answerable question

Defender A preserves the received lure and its receipt record. A referenced destination becomes
a lead, not proof that its operator sent the message or that anyone followed it. Attachments and
links stay inert until an admitted analysis step. Received material, authorized records, permitted
public sources, and voluntary peer evidence supply the investigation.

Give the lead an answerable question and explain why pursuing it could help. Retain supporting
and contrary evidence, competing explanations, permitted sources or tests, expected contribution,
effort ceiling, expiry, and stopping condition. The agent may pursue that admitted lead without
asking for each reasoning step. A new target, method, or disclosure outside its scope needs
separate admission. When the allowance is exhausted, return findings and explicit gaps rather
than inventing an answer.

A verification lead can ask whether a suspected weakness is reproducible within the authorized
scope or whether an applied repair closes it. Keep the exact tested revision, conditions, and
limits with the result. A passed test supports that tested claim; it does not certify the whole
environment or authorize deployment.

## Ask another defender

A asks an eligible peer whether it observed the destination during a bounded interval. The
request binds its recipient, purpose, minimal matching features, exact outgoing bytes, period,
authority, expiry, and response-size/fan-out limits. The receiver independently admits the work
and any response. It may return evidence and suggest a lead without acquiring control of A's case.

| Response | What it establishes |
| --- | --- |
| Matching observation | The contributor observed the stated facts by the stated method, within its coverage. |
| No matching observation | The permitted search found nothing in its declared scope; activity outside it remains unknown. |
| Withheld or unavailable | A result cannot be disclosed or produced. The distinction must not expose whether a private case exists. |
| Correction | A recipient-scoped claim is revised or withdrawn, with affected conclusions and delivery accounted for. |

Evidence can remain with its owner, with enough permitted support for independent challenge.
Each exchange fixes retention and redistribution rules. Queries, their combinations, and derived
findings can expose a victim just as attachments can; pseudonyms or hashes alone do not establish
anonymity. An audience label is not access control. This exchange exposes no private-case
inventory, raw mailbox, bearer artifact link, or raw canonical source digest.

Use a permitted observable for matching when necessary. A scoped evidence digest accounts for
evidence; it does not supply a private matching protocol between peers. Enrollment, revocation,
query-abuse controls, and cross-community trust need their own design and evidence before live
exchange. [Security](../../adr/09-security.md#portal-privatization-and-egress) owns disclosure;
[Intercom](../../adr/26-a2a.md) owns sovereign peer-task transport.

## Establish the relationship

B reports an earlier matching attempt; C contributes later use of a compromised account. Thorn
keeps a versioned timeline and relationship map. Every proposed link carries its source, relation
type, time interval and clock uncertainty, observed or inferred status, and alternative explanations.
Each participant sees only the victim references and observations it may receive.

Distinguish **receipt → attempted access → successful access → subsequent use**. Ordering these
events does not prove movement between systems. A missing hop stays missing. A shared address,
hosting provider, writing style, or generated lure can support comparison without proving common
control. Keep **indicator, infrastructure, campaign, automated actor, account user, and human
controller** separate. A compromised machine or account may belong to another victim.

Copied reports retain their common origin; signatures establish contributors, not allegations.
Even independent observers can collect identifiers planted by one adversary. Separate observation
independence from grounds for operational control. Test borrowed, planted, or compromised
infrastructure explanations before making a consequential association. When available evidence
cannot distinguish them, retain the narrower finding and the next discriminating question.

An admitted lead might check whether B recorded a completed session, whether C observed the same
destination, or whether the clocks support the proposed order. Findings can merge, split, reject,
or revise a campaign hypothesis. Peer counts cannot settle attribution or trigger a shared
blacklist. **Controller unknown** is a useful outcome when the supported activity is clear.

## Keep hostile material from directing the investigation

Attacker artifacts, suspected coordination messages, peer returns, tool outputs, summaries, and
recalled claims remain attributed evidence. They cannot recruit a defender into new goals or
grant tools, targets, disclosures, or budget. Observing a coordination channel supplies no right
to enter private communications or join the attacking activity.

Assume a reasoning worker can be fully compromised. Preserved originals, permissions, budgets,
effect admission, and the supervising stop remain outside its control under
[Security](../../adr/09-security.md#7-return-quarantine). A second model or detector cannot replace
that enforcement. Keep source and transformation dependencies, including producing model/tool
generation and occurrence, so a challenger can inspect permitted underlying evidence and gaps.

Quarantine suspect contributors, sensors, and derivatives from consequential use pending review.
Incomplete lineage restricts affected use until supported reconstruction; it cannot restore trust
by omission. Reassess dependent reports while retaining earlier effects and correction obligations.
Incident material does not automatically become standing instructions, cross-case memory, or
training data; [Archive](../../adr/27-memory.md#ingestion) governs that passage.

## Add a source only for a missing observation

An additional collector must answer an identified detection or investigation need. Pin authorized
infrastructure, source generation, capture method/scope, time coverage, storage and retention,
permitted export, resource limits, and a stop outside its control. Importing a log grants no
administrative rights over its source system.

Before exposing a collector, establish observed isolation from private home and control-plane
resources, restricted egress, and the absence of production credentials or relay/pivot capability.
Admit capture and export separately. Keep hostile bytes quarantined through parsing, rendering,
storage, and analysis.

If the collector is compromised, remove its ingress/export authority, preserve permitted
evidence, and review its output. Rebuilding requires a newly admitted generation; reconnecting
the old one cannot restore trust. Any period of silence means only what the known coverage can
support.

## Return findings and keep them correctable

The case returns supported activity, known reach, disputed links, gaps, and useful next actions.
Warnings and reports follow the [case's reporting contract](index.md#reports-and-corrections),
with evidence proportionate to the recipient and requested intervention. Local protection stays
scoped, reviewable, expiring, and subject to an explicit recovery decision.

A challenged claim updates its timeline links, dependent conclusions, and recipient-specific
correction obligations together. A closed inquiry can still owe corrections. The
[response policy](response-policy.md) bounds pursuit and participation; [Trials](trials.md) tests
whether the added evidence improves a decision at acceptable cost.

[Thorn](index.md)
