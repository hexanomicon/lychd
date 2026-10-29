---
title: Accounts and updates
icon: material/account-cog-outline
---

# :material-account-cog-outline: Accounts and updates

The operator chooses **Connect Gmail**, **Install Discord**, or **Install GitHub**, sees the exact
account and requested access, then chooses where Reach may read and speak. The first success is a
confirmed connection and a prepared message; sending a test message remains a separately admitted
action.

This is the onboarding and custody proposal for the [connected-work study](index.md), not an
existing settings screen or deployment profile. Optional [WhatsApp](whatsapp.md) adds its own
business/number onboarding or separately qualified owner–agent route; it is not another Google-style
account grant or a dependency of the first three connections.

## Registration, connection, policy

Keep three acts visible. The application publisher registers the provider application once. An
account owner or administrator authorizes one account, guild or repository installation. The local
operator assigns Reach policy under Ward. A provider consent screen settles only the second act.

Each connected account retains a separate local identity and credential binding, even when the
same person works for several companies. The selected sender is visible during preparation and
review. Account discovery never silently links personal Gmail with a workplace, selects all
repositories, or enrolls external senders as local Users.

| Deployment choice | Customer setup | Secret custody and cost |
| --- | --- | --- |
| **Customer-owned applications, self-hosted authority** | Create/import exact Google, Discord and GitHub registrations, then authorize selected accounts. GitHub's manifest flow can reduce registration work. | App credentials and tokens stay at that installation. More first-install work; no shared publisher credential in customer packages. Recommended first road for the operator. |
| **Publisher-operated applications and service** | OAuth account consent or provider install link, followed by local audience/policy selection; administrators may need to approve access. | Publisher operates credential gates, callbacks, isolation, recovery and provider verification. Lowest recurring customer setup; a real hosted service obligation. Candidate later distribution road. |

A shared Discord token covers multiple guilds. A shared GitHub App signing key can obtain tokens
for its installations. Neither is a separate customer secret merely because a connection row is
separate. A self-hosted client must not receive the publisher's shared secret. A future credential
broker would need an exact per-installation protocol, custody/disclosure manifest and independently
authorized destination; it is not supplied by a generic OAuth proxy or by this study.

For Google, a shared confidential server client also stays with its trusted service. Customer-owned
registrations use their own exact callback. No wildcard callback or reusable authentication code
is accepted. A native installed-client flow would be a separately admitted deployment choice,
not a confidential server secret copied into a client.

## Connection lifecycle

`UNCONFIGURED → AUTHORIZING → ACTIVE` records installation/authorization and explicit account
confirmation. `DEGRADED` means transient service or quota failure; `REAUTH_REQUIRED` means expired or
revoked authorization; `SUSPENDED` means operator/provider policy denies work; `DISCONNECTED` closes
the connection. Status distinguishes these from a disconnected host and from unknown deliveries.

To authorize a connection, bind the authenticated local initiator to the chosen provider/client,
exact callback, short expiry, one-use state and PKCE where supported. Only the credential owner
may redeem and validate the grant, and activation must wait for confirmation of immutable provider
identity. Reconnection must retain an existing refresh token when the response omits one. Serialize
concurrent refreshes per connection and fence them by generation, so a late response cannot revive
a revoked grant.

Persist bearer tokens encrypted with separately scoped key custody. Configuration and database
records carry secret references; prompts, checkpoints, logs and ordinary backups carry no usable
bearer or decryption key. Restore must explicitly recover or reenroll the credential generation.

Disconnect in custody order: close admission and fence queued sends first, then stop watches/
subscriptions and retire that connection's authorization, installation binding and derived tokens.
A shared Discord bot token or GitHub App signing key also serves other installations; disconnecting
one guild/repository must not revoke it. Retiring an app-wide credential is a separate administrative
operation that enumerates and fences every affected connection.

Disconnection does not settle a send already submitted: that effect still needs reconciliation.
Remove content according to retention and holds, preserving the minimal lawful effect identity
needed to prevent replay. Deletion cannot erase a recipient's copy. On reconnection, confirm identity
and policy again; a valid token alone cannot release an old pending send.

## What an update asks of the user

| Change | Proposed handling |
| --- | --- |
| Bug fix or new logic within the existing contract and provider grant | Quiesced LychD generation update; retain connection ids, credential custody, cursors and effect identities. No routine provider reconnect or reinstall. |
| New optional provider capability | Keep disabled until its exact adapter/profile, local policy and required provider permissions are admitted. |
| Additional Google scopes or GitHub permissions; wider Discord access | Explain the increment and obtain provider/account-administrator authorization where required. Old installations keep their previous access until granted. |
| Revoked/expired grant, administrator block, lost key or changed client identity | Suspend affected work and request the exact repair. No retry loop or fallback to a different account. |
| Callback/host/custody change or schema/contract change | Explicit configuration/migration under Evolution; reauthorization when the provider requires it. Never drop outbox/dedupe state to make an upgrade pass. |

The lack of a provider prompt for an ordinary code release is an inference from the providers'
separation of application registration and runtime code; it is an acceptance target to verify,
not a promise that no provider will ever change its requirements. Executable extensions still
follow LychD's [one-process-generation rule](../../../adr/05-extensions.md#one-process-one-extension-generation).

## First deployment road

Propose `reach.home.connected@1`: one authority-host generation, outbound Discord Gateway/REST,
Gmail REST synchronization, and GitHub REST polling. Browser-based account authorization needs an
exact admitted callback reachable by that browser; steady-state polling does not need a public
webhook listener. An ordinary loopback application must not be exposed to create that callback.

Private mail and credentials remain at the authority host in separately scoped trusted services.
An optional remote ingress edge initially carries only bounded event hints whose provider state
the authority refetches; it cannot assert an enrolled caller or receive private Context. Public
Discord profiles remain unchanged and cannot become private-mail profiles through configuration
flags. Shared signing keys and bot tokens require a separately bounded publisher service road.

Before activation, the registered manifest must specify the exact services, secret references,
sockets, outbound destinations, callback routes, resource limits, migrations, authority epochs,
retention and restart/compromise recovery. If custody moves, fence the old generation and reconcile
pending effects before activating the new owner. Rotating its secret does not establish whether an
uncertain send occurred and cannot make that send safe to repeat.

The existing missing Ward, Composition selection, service-attempt and deployment prerequisites
remain delivery gates, recorded in [State](../../../state-of-the-work.md#composition-portfolio-delivery).
This proposal creates no service, port, token store or permissive local-authority substitute.

WhatsApp Cloud API would require the separately admitted webhook profile described in its
[assessment](whatsapp.md#intake-requires-a-different-deployment). Its message bodies are not
refetchable event hints by assumption; it cannot inherit this outbound-only road unchanged.

[Gmail](gmail.md) · [Discord](discord.md) · [GitHub](github.md) · [WhatsApp](whatsapp.md) · [Delivery plan](delivery.md)
