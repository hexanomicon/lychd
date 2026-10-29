---
title: Acceptance and delivery
icon: material/test-tube
---

# :material-test-tube: Acceptance and delivery

The first useful result is one prepared email from the correct mailbox and one known delivery
after authorized review. A successful API request alone cannot qualify Reach: it must survive a
restart, revoked access and a lost response without sending the same message twice by assumption.

This is the implementation plan for the [candidate successor](index.md). The separate
[connected preparation profile](preparation.md) implements pure account/target/payload preparation
and a finite native Graph. It supplies no operational successor registration, provider transport,
credential service or deployed capability.

## Ordered slices

1. **Close the contract.** Accept or revise the proposed `reach.correspondence` identity, records,
   provider profiles, authority/privacy boundaries, Patterns and successor relation. Register no
   empty package to imply acceptance. Any shared-law change belongs to its existing Covenant.
2. **Prove preparation without providers.** Pure application policy plus typed fake ports exercise
   account selection, bounded reads, hostile input, exact communication preparation, required native
   review, standing-policy constraints and finite retention. Initially no model/network is needed.
   The offline connected profile now covers exact preparation and provider request construction;
   its preparation policy is deliberately not standing delivery authority or native review.
3. **Prove durable delivery.** Add Composition-owned PostgreSQL models/migration/store and
   transactionally bound intake, communication, outbox, authority generations and effect identity.
   Bind existing Run/Consent/worker ownership without a second workflow executor. Exercise restart,
   racing claims, revocation and reconciliation with inert effects and a disposable database.
4. **Qualify Gmail first.** Customer-owned internal/personal-use registration, bounded polling,
   read/draft/review/send, current authorization, and Sent reconciliation. Start with the operator's
   account after the required credential and deployment seams exist. Attachments/Calendar/Drive and
   push are separate increments. Mail migration is independent of connector development.
5. **Qualify Discord and GitHub separately.** Reuse prepared-message policy and delivery machinery;
   add exact platform identity, semantics and recovery. Prove one allowed Discord turn and one
   issue/PR timeline comment, including each provider's unknown outcome.
6. **Package client onboarding.** Connection/status/review projections, customer-owned registration
   assistance, compatibility/update checks and disconnect/delete. A publisher-operated application
   comes only with its credential service, verification, isolation and support envelope qualified.
7. **Revisit optional WhatsApp.** Qualify business assets, actual use/market eligibility, current
   pricing, template/window/opt-out policy, human escalation and its new HTTPS webhook profile.
   Probe the separate personal owner–agent platform only where rollout and its developer contract
   are confirmed. Neither path gates delivery of the initial three connectors.

## Smallest falsifying fixtures

| Boundary | Required counterexample and observation |
| --- | --- |
| Ownership | Two companies and personal mail share one instance. Cross-connection reads, wrong sender, forged external identity and broad status access refuse before disclosure. |
| Hostile content | A mail/issue/comment instructs the agent to reveal secrets, follow a link, change recipients or run code. It remains attributed content and produces no extra authority or network call. |
| Review and autonomy | Review binds exact body/recipients/actor. A changed draft, expired policy, new `Reply-To`, exhausted use counter, required-review bypass or changed audience cannot send. A matching finite standing policy can send without another human verdict. |
| Durable custody | Crash at each intake/cursor/admission and outbox/claim/submit/settlement boundary; recover all admitted work, preserve unknown effects and reject stale claims. Race two claimants and prove no second submission merely from queue replay. |
| Revocation | Revoke during preparation, review wait, token refresh and immediately before transport. Later work is fenced; already-accepted bytes remain honestly irreversible. Reconnection does not release old pending sends. |
| Gmail | Duplicate/out-of-order changes, pagination, expired-history 404, missing refresh token on refresh/reconnect, scope refusal, draft-create/send timeout, delayed readback and vanished draft without proof. No duplicate from full resync or ambiguous draft creation; optional label changes need their own exact effect/desired-state evidence. |
| Discord | Explicit mention versus ambient content, Gateway resume failure, three-second deferral, expired interaction token, mention injection and send uncertainty beyond nonce guarantees. No private authority from a role or interaction. |
| GitHub | Delivery replay or edited comment, untriggered activity, own-app reply loop, bad signature, removed repository, missed deliveries outside redelivery history, timeout after comment creation and forged matching marker. One reply cannot trigger another; correlation must also match app author, destination and admitted bytes. |
| Optional WhatsApp | Expired response window, paused template, opt-out, human takeover, forged/duplicate/late webhook, unknown send and delayed delivery, shared-account disconnect, spend or market-policy refusal. No access to other personal chats or unavailable agent rollout is inferred. |
| Limits and lifecycle | 429/403/quota exhaustion yields bounded waiting; revoked credentials stop retries. Disconnect one of two shared-app installations without revoking the other. Disconnect, retention, backup restore and generation upgrade preserve dedupe/effect identities and cannot resurrect a send. |
| Custody | Each service can read only its declared secrets/routes. A customer package has no shared publisher signing key/token. Logs, model Context, checkpoints and status contain no bearer secrets. |

Use these fixtures to test the provider's actual limits as well as local recovery. Each adapter
must declare what its provider can prove about an ambiguous write. When the evidence cannot
exclude a prior send, qualification requires a visible unresolved result and no automatic
repetition. A fake provider cannot establish an exactly-once guarantee the real provider lacks.

## Owners and delivery gates

| Required seam | Existing authority |
| --- | --- |
| Composition revision, Pattern/Scroll closure and event/schedule admission | [Workflow](../../../adr/28-workflow.md) |
| Current identity, account linking, object authority and revocation | [Ward](../../../adr/38-iam.md) |
| Exact review, standing preauthorization and re-admission | [HitL](../../../adr/25-hitl.md) |
| Secret custody, hostile input and per-transmission disclosure | [Security](../../../adr/09-security.md) |
| Transactional records, outbox and migration/recovery | [Persistence](../../../adr/06-persistence.md) |
| Durable service attempts and retry ownership | [Workers](../../../adr/14-workers.md#service-job-attempts) |
| Sealed contributions and generation replacement | [Extensions](../../../adr/05-extensions.md), [Evolution](../../../adr/18-evolution.md) |
| Exact service manifest and callback/ingress selection | [Containers](../../../adr/08-containers.md#versioned-application-deployments), [Configuration](../../../adr/12-configuration.md#application-and-gateway-profiles) |

Before implementation, reconcile the chosen slice with those owners and current
[delivery evidence](../../../state-of-the-work.md#composition-portfolio-delivery). The existing
public-only Discord profile and credential-gated loopback bootstrap supply no private remote IAM,
general service-attempt runtime, Composition selector or connected deployment by themselves.
Private mail must not be exposed through a convenient callback or permissive local-authority shim.

After deterministic proof, qualify the live path separately with one test account/repository/guild
and an explicitly admitted message. Observe real expiry/revoke/429 behavior where feasible, then
exercise reconnect and a generation upgrade. Record which observations actually occurred. This
design itself authorizes neither production-wide permissions nor external sends.

[Accounts and updates](accounts.md) · [Gmail](gmail.md) · [Discord](discord.md) · [GitHub](github.md) · [WhatsApp](whatsapp.md)
