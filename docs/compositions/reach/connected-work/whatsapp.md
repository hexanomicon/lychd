---
title: WhatsApp assessment
icon: fontawesome/brands/whatsapp
---

# :fontawesome-brands-whatsapp: WhatsApp assessment

A customer asks a business a question on WhatsApp. Reach can prepare an answer and deliver it from
the business's number, subject to the recipient's permission, the response window and current
provider policy. That is useful correspondence; it does not establish access to the operator's
existing personal chats.

Reviewed **2026-10-21** for the [connected-work study](index.md). Recommend an **optional later
Business Platform profile**, `reach.whatsapp.business@1`, after the Gmail, Discord and GitHub
slices. It reuses Reach's preparation, authority and effect ledger but needs its own intake,
onboarding, eligibility and billing contracts. No WhatsApp connection is implemented or qualified.

## Three distinct routes

| Route | Useful result | Decision |
| --- | --- | --- |
| **Business Platform / Cloud API** | Receive customer messages and send from the admitted business number. | Candidate for bounded business correspondence. No personal-inbox or arbitrary existing-group import promise. |
| **General-purpose assistant over Business Platform** | A person chats with an AI assistant through its business-platform number. | Separate usage classification and current market gate. Do not disguise the primary product as ordinary customer support. |
| **Third Party Agent Platform** | The owner chats directly with their connected agent. | Separate limited-rollout probe; not the Cloud API business profile or a presently qualified Reach adapter. |

WhatsApp's official [agent help](https://faq.whatsapp.com/1050934623978152) describes up to five
connected agents, each accessible only to its owner and unable to enter or read other chats.
Availability is limited; these agent chats use Meta's service and are not considered end-to-end
encrypted. Their [Agent Terms](https://www.whatsapp.com/legal/third-party-agents-terms) apply to that
specific platform. Before proposing its adapter, verify the developer protocol, account/country
availability, sender assurance, callback custody and reconnect/recovery in the actual deployment.

The business profile uses official APIs. Reverse-engineered WhatsApp Web sessions, browser cookies
and QR-linked session libraries are outside this candidate and supply no supported shortcut to
personal-chat access.

## Business setup and existing numbers

Own-business setup needs the Meta application, business portfolio, Messaging account (older APIs
and docs call this WABA), registered business phone identity, and production token custody. Use
the necessary `whatsapp_business_messaging` permission; management access belongs only to the
setup/management service that actually requires it. Test tokens are not unattended production
credentials. [Get started](https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started)

Serving other firms is a separate publisher road: partner/Tech Provider eligibility, Embedded
Signup, required Advanced Access/App Review and each customer's own assets/grants. A provider
partner may reduce development work but adds custody and fees. Self-hosting does not bypass those
requirements. Disconnect one customer without rotating a shared Meta application secret or
disrupting other accounts. [Webhook access requirements](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview)

Coexistence can connect an eligible **WhatsApp Business app** number while preserving app use; it
is not generic consumer-WhatsApp OAuth. Its onboarding requires the supported partner/Embedded
Signup flow. Optional consented history transfer has a bounded window; group chats do not sync.
Human sends can produce message echoes and do not extend the Cloud API response window. Preserve
the existing account until migration/coexistence eligibility is established; no automatic number
conversion is proposed. [Business-app onboarding](https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-business-app-users)

An official Groups API exists with its own eligibility and constraints. It is deferred here;
existing personal groups are not inferred to be accessible. [Groups](https://developers.facebook.com/documentation/business-messaging/whatsapp/groups)

## One permitted send

The [Messaging Policy](https://whatsappbusiness.com/policy/) requires recipient permission and
honored opt-outs. Free-form replies use the **24-hour customer service window**, refreshed by the
customer's message. Outside it, only eligible approved templates may be sent. Automation must offer
a clear escalation path to a person or business support. A template's approval does not authorize
its recipient, purpose or data disclosure.

First establish what use the connection admits. Its policy pins own-business versus AI-provider
use, business/account/phone ids, exact recipient identity, permitted purposes, opt-in/opt-out
evidence and current market rules. Each prepared send then binds the triggering message, last
eligible inbound time, conservative `latest_send_at`, message type, exact text or template
revision/language/parameters, and spend ceiling. Recheck all of these, together with current
provider eligibility, immediately before transmission.

An expired free-form reply parks or refuses; never silently convert it to a charged template.
Paused/rejected templates, opt-out, quality restriction or exhausted budget fence queued work.
Customer requests for a person or an observed manual reply can pause automation under the
conversation policy. A later resumption rechecks the window and authority rather than replaying
the old reply. Escalation itself grants no code, payment or private-record authority.

## Intake requires a different deployment

Cloud API receives messages and status through webhooks. Propose
`reach.home.connected_webhooks@1`: one authority host with an exact admitted HTTPS/Veil webhook
route, bounded raw-body intake and provider verification. The outbound-only
[`reach.home.connected@1`](accounts.md#first-deployment-road) stays unchanged. A new public route
cannot be implemented by exposing the current loopback bootstrap application.

Setting up the webhook and admitting a message require different proofs. Validate GET setup
challenges separately; for a POST, verify `X-Hub-Signature-256` over the original body with the scoped
Meta application secret. The setup verify token is not the signature secret. Before durably
admitting the POST, check configured app/account/phone ownership, allowed event kind, bytes and
generation. Acknowledge only after committing custody of that bounded intake. [Webhook endpoint](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/create-webhook-endpoint)

Deduplicate incoming provider message ids within the account/phone partition. Status updates need
their own message/status/event fingerprint; a delivered or read event is not another customer
request. Ignore own-message echoes as triggers. Retries may continue for up to seven days; provider
retry is not a complete history API. Record gaps and avoid promising Gmail-style full resync.
No remote edge carrying only refetchable hints can recover an unretained message body by assumption.
[Webhook delivery](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview)

A successful send returns a `wamid`; retain it to correlate later sent/delivered/read/failed
observations. The initial success does not prove delivery, and a later read observation does not
prove comprehension. `biz_opaque_callback_data` may carry a random effect correlation, but no
secret/customer metadata and no implied idempotency guarantee.

Keep an ambiguous send `UNKNOWN` until authenticated matching status or other independent evidence
resolves it. Without that evidence, stop instead of repeating the send. Provider queue TTL can also
delay an accepted message, so the contract assumes no instant cancellation.
[Send semantics](https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/send-messages),
[status events](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/reference/messages/status)

## Pricing, AI eligibility and maintenance

Do not encode “all replies within 24 hours are free.” The official [dated pricing FAQ](https://whatsappbusiness.com/resources/faq/)
states that from **2026-10-01** ordinary service messages are priced per delivered message, with
the first 1,000 monthly service messages per business phone free. Resolve the actual category,
market, rate card, free allowance, provider fees and any exception; reserve spend before sending
and reconcile observations. Enforce current throughput, recipient, quality and messaging limits
with bounded backoff rather than fixed universal rates.

General-purpose AI has distinct restrictions and pricing. Current [AI-provider documentation](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/ai-providers),
updated **2026-10-15**, includes EEA recipients such as Slovakia, Brazil and Türkiye under different
conditions; EEA service traffic has a specific exemption. This is not a universal AI ban or a
permanent worldwide permission. Pin a current eligibility observation and refuse an unknown or
expired market/classification. The [Platform Terms §4.7](https://www.facebook.com/legal/Meta-Terms-for-WhatsApp-Business-Platform),
modified **2026-09-23**, distinguish primary AI products from ancillary AI business service and
restrict model training/data reuse. Older March terms are not the current contract.

Ordinary adapter releases retain asset, secret, subscription and effect identities. New permissions,
number/custody changes, template versions and provider Graph API deprecations need their own
admission or administrator action. Automation cannot replace Meta eligibility or make an unavailable
personal agent rollout available.

Before qualifying delivery, exercise window expiry during a queue wait, template pause, opt-out
and human takeover. Also test duplicate/late webhooks, forged signatures, shared-customer
disconnect, unknown sends, exhausted spend, market-policy changes and unavailable agent rollout.
These cases must challenge the promised behavior. The common [acceptance plan](delivery.md) and
the initial three connectors remain independent of this optional work.

[Chat](../chat.md) · [Accounts and updates](accounts.md)
