---
title: Home-only
icon: material/home-lock
---

# :material-home-lock: Home-only

Reach sleeps when home sleeps. `reach.home.public@1` keeps its Ward, Vessel, Workers, corpus, effect ledger, and Phylactery in one home-local `ApplicationDeploymentManifest@1`, with no VPS, Tether, Veil, public listener, callback, or inbound A2A road.

This profile is **Designed, not deployable**. [State of Work](../../../state-of-the-work.md#composition-portfolio-delivery) records Reach’s delivery boundary.

The profile admits public corpus/Context and guest effects. Its separated services narrow parser and credential compromise, but do not isolate the body from home-account or Vessel compromise, which may expose private home truth and resident credentials.

## Services and roads

The Discord edge holds the bot token and Gateway/event/delivery observations. It has no provider credentials, corpus writer, database secret, policy, or ambient Sigil. Core/Ward/Workers own admissions, task Sigils, Runs, turns, and policy, but receive no bot/provider bearers, non-local listeners, or host control.

Fetching evidence and making remote attempts also have separate owners. The corpus refresher holds allowlisted HTTPS access and staging custody; the Portal/A2A gate holds only the credentials and attempts for its exact destination. Phylactery owns canonical Core/Reach records and has neither a non-local listener nor a replica.

Gateway WSS and Discord REST, source HTTPS, and exact provider/A2A HTTPS are outbound. Authenticated typed local ports connect services; other ingress is closed. The [standalone E2E contract](vps-public.md#first-e2e-contract-one-public-discord-question) supplies the same corpus, fresh egress, quarantine, turn, nonce, and known/unknown delivery law. Every canonical record commits at home.

## Failure and recovery

After reboot, use Run/outbox truth to resume safe pre-submit work and reconcile uncertain provider/Discord effects. Reconnecting recovers only the events Discord still supplies, so older missed events have no promised recovery. While power or Internet access is lost, Reach performs no cognition, provider/A2A work, or delivery.

Home compromise closes admission, revokes bot/provider/A2A/database/service credentials, and reconciles external identities. Recovery follows the [clean-rebuild contract](vps-public.md#restart-uncertainty-and-compromise): rebuild a trusted body, restore only independently verified non-secret records from an admitted backup, and reenroll from zero authority before activating a fresh epoch. An off-host backup cannot operate as a second Phylactery.

## Acceptance

Qualification must follow a public turn across two boots and prove dedupe, corpus citations, and per-attempt egress. It must also exercise uncertain provider/A2A and Discord effects, service-secret/network isolation, zero non-local listeners, and restore. Private Context, consequential effects, callbacks, inbound peers, and simultaneous epochs must all refuse.

[Deployment matrix](index.md) · [Reach turn](../turn.md)
