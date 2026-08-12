---
title: Home-only
icon: material/home-lock
---

# :material-home-lock: Home-only

`reach.home.public@1` is the default when the operator wants durable Reach truth at home and can
accept that Reach sleeps with the home host. One home-local
[`ApplicationDeploymentManifest@1`](../../../adr/08-containers.md#versioned-application-deployments)
places the authoritative Ward, Vessel, Workers, corpus, effect ledger, and Phylactery on that host.
It has no VPS, Tether, Veil, public listener, callback, or inbound A2A route.

This is public/guest Reach policy, not isolation from the rest of a home body. The profile admits
only explicitly public corpus/context and guest effects; manifest-separated services still prevent
ordinary parser or credential compromise from becoming ambient access. A compromise of the home
account or Vessel may nevertheless expose private home truth and every resident credential.

## Services and roads

| Service | Holds | Must not gain |
| --- | --- | --- |
| Discord edge | bot token; Gateway cursor; Discord event/delivery observations | provider/A2A secret, corpus writer, database secret, policy, ambient Sigil |
| Reach core, Ward, Workers | admissions, task Sigils, Runs, turns, policy | bot/provider bearer, public listener, host control |
| Corpus refresher | admitted HTTPS origins and snapshot build custody | provider/bot bearer, application effects |
| Portal/A2A gate | exact destination credential and external attempt custody | Discord delivery or corpus-write authority |
| Phylactery | every canonical Core and Reach record | non-local listener or cross-host replica |

The Discord edge opens outbound Gateway WSS and Discord REST HTTPS. Corpus acquisition opens only
admitted outbound HTTPS origins. The provider/A2A gate opens only its exact outbound HTTPS
destination. Internal calls use authenticated typed local ports and all other ingress is closed.

The profile uses the same public-corpus, fresh `EgressDecision`, return-quarantine, durable turn,
deterministic Discord nonce, and known/unknown delivery contracts as the
[standalone VPS](vps-public.md#first-e2e-contract-one-public-discord-question); only placement and
compromise domain differ. Every named canonical record commits in the home Phylactery.

## Failure and recovery

On reboot, durable Run/outbox recovery resumes safe pre-submit work and reconciles uncertain
provider or Discord effects. Gateway reconnect can recover only events Discord still makes
available; this profile makes no promise for older missed events. During a power or Internet
outage, no cognition, provider/A2A call, or Discord delivery occurs.

Home compromise closes admission, revokes bot, provider/A2A, database and service credentials,
reconciles external identities, restores from admitted home backup, and activates a fresh epoch.
An offline backup may be copied elsewhere, but never runs as a second Phylactery.

## Acceptance

Prove one clean two-boot public Discord turn, exact event dedupe, public-corpus citation binding,
per-attempt egress decisions, restart-safe provider/A2A and Discord uncertainty, service-secret and
network isolation, zero non-local listeners, backup restore, and refusal of private Context,
consequential effects, callbacks, inbound peers, or simultaneous profile epochs.

[Deployment matrix](index.md) · [Reach turn](../turn.md)
