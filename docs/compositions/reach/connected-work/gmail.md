---
title: Gmail connection
icon: material/gmail
---

# :material-gmail: Gmail connection

The operator connects one mailbox, selects the mail Reach may inspect, and prepares a reply from
that account. Connecting a second employer creates another connection, not a shared inbox or
permission to combine the two companies' Context.

This candidate profile, `reach.gmail.correspondence@1`, belongs to the
[successor study](index.md). Gmail-enabled personal accounts and Workspace accounts can use the API;
Business Standard is not a prerequisite. [Google's prerequisites](https://developers.google.com/workspace/gmail/api/quickstart/python)
require a Cloud project and Gmail access, not that subscription.

## First registration and customer friction

| Use | Proposed registration | Operational consequence |
| --- | --- | --- |
| Operator's own Workspace | Organization-owned Cloud project, Internal audience, same-organization users. | Internal verification exception; the administrator still controls access. |
| Operator's personal Gmail | Personal-use OAuth project, External audience and production publishing state. | Personal-use exception may apply; unverified warning/user limits remain. Testing is a development state, not durable unattended operation. |
| One client firm's internal deployment | Its organization-owned project and Internal audience for its own users. | Repeat registration per customer, with separate custody. Self-hosting alone creates no exception. |
| One shared application serving unrelated firms or the public | Publisher-owned External application. | Plan brand/scope verification and, where restricted data is accessed through servers, the applicable independent security assessment and recurring review. |

The [restricted-scope review rules](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification)
define the exemptions and annual assessment obligation. Confirm applicability against the actual
deployment/data path before promising a commercial onboarding flow or cost. Buying Workspace
does not verify a publisher's application for other companies.

External Testing grants with Gmail scopes ordinarily expire after seven days. Google's current
[app-state guidance](https://developers.google.com/identity/protocols/oauth2/production-readiness/overview)
documents an organization-local override when its Workspace administrator marks an app Trusted.
That is an admin-governed pilot option, not public verification or an Internal audience spanning
unrelated firms. A verified app can still be blocked by an administrator.

Use a dedicated agent-workflow OAuth client. Google's [client guidance](https://support.google.com/cloud/answer/15549257)
separates AI-agent and ordinary interactive clients when both coexist. The REST quickstart makes
the agent checkbox optional; the announced MCP enforcement is not a universal REST requirement.

## Consent and capability closure

The server authorization-code flow requests offline access, uses the exact registered callback,
and keeps refresh tokens with the credential owner. Ordinary token refresh needs no user click.
Retain an existing refresh token when a later response omits it. Invalid/revoked grants stop work
and enter `REAUTH_REQUIRED`; new permissions require explicit incremental authorization.
[Offline OAuth](https://developers.google.com/identity/protocols/oauth2/web-server)

Request minimal `openid`/`email` identity scopes as well as the selected Gmail scopes. Validate the
ID token's issuer, audience, expiry and flow binding; retain `(issuer, sub)` as the account identity,
with email only as display/routing data. Mail headers cannot establish that binding.
[Google identity](https://developers.google.com/identity/openid-connect/openid-connect)

| Requested capability | Provider scope | Local restriction |
| --- | --- | --- |
| Search and read selected messages/threads | `gmail.readonly` | Restricted scope; query/label selection is a Reach boundary, not provider-enforced isolation within the mailbox. |
| Save drafts and send | `gmail.compose` | Restricted scope; it already permits sending. Review-only mode must be enforced locally. |
| Optional labels, archive and read-state changes with read/draft/send | `gmail.modify` | Restricted and broader than those named actions; replace narrower grants only when required. Exclude trash/settings/destructive operations locally. |
| A separate send-only integration | `gmail.send` | Sensitive scope; cannot serve an inbox-reading agent. |

Avoid full `https://mail.google.com/` access. [Google's scope table](https://developers.google.com/workspace/gmail/api/auth/scopes)
is the authority for classification and scope coverage. Calendar, Drive and mailbox administrative
settings are later separately authorized capabilities.

## Mailbox writes are separate effects

Saving a draft discloses its body to Google even when no recipient receives it. Proposed
`ReachMailboxMutationIntent@1` and `ReachMailboxMutationReceipt@1` bind one connection, operation,
exact message/draft ids, MIME or label delta, preparation/observation, authorization, expiry,
effect identity and fenced attempt. Use the same durable outbox states and current byte-time
disclosure checks as delivery; creating a draft does not consume or imply send authority.

The first draft operation creates a Reach-owned snapshot and retains the returned draft id.
Ambiguous creation remains `UNKNOWN` until matching draft content/correlation is reconciled;
never retry creation merely because one list call did not find it. Updates to human/shared drafts
are deferred: Gmail read-before-write alone supplies no atomic compare-and-swap guarantee.
Revised preparation stays local or creates a separately admitted snapshot, without overwriting an
existing draft. The first send path submits sealed MIME directly rather than mutable draft bytes.

Optional label/read/archive changes bind the exact message set and add/remove label ids. Repeated
application is eligible only when that adapter contract proves the same desired-state operation
safe and current authority still admits it. Readback can establish observed desired state, not
exclusive authorship of a change. Unknown or conflicting observations stop for reconciliation;
trash and deletion remain excluded. [Message label changes](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/modify)

## Synchronization and sending

Start with outbound incremental polling and a bounded initial synchronization; persist a mailbox
history cursor. A later push option uses Pub/Sub: create a topic in the calling project, grant
Gmail publication, and select authenticated push or outbound pull. Renew `watch` before expiration
(Google recommends daily; at least every seven days). Notifications are wakeups, not message
contents or complete event history. Persist admitted changes and finish pagination before advancing
the processed cursor. Repeated/out-of-order notifications cannot create new sends.
[Push contract](https://developers.google.com/workspace/gmail/api/guides/push)

Expired Gmail history returns **404**. Rebuild the purpose-bounded projection with a new full sync;
do not replay every rediscovered message as a fresh request. A new watch baseline cannot overwrite
an unprocessed cursor. [Synchronization](https://developers.google.com/workspace/gmail/api/guides/sync)

Freeze canonical MIME, sender/alias, recipients, reply headers and body before review or standing
policy admission. Verify an alias is eligible; an alias shares the mailbox's limits and is not a
separate identity grant. Gmail's send API documents no idempotency key. Retain an application
effect id and RFC Message-ID for correlation, then the returned Gmail message id. A timeout after
submission stays `UNKNOWN` while Sent mail is inspected. Matching author, destination, bytes and
correlation can support reconciliation; absence in one read cannot prove non-delivery. A vanished
draft is insufficient evidence. Provider acceptance is not final delivery.
[Send API](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send),
[draft lifecycle](https://developers.google.com/workspace/gmail/api/guides/drafts),
[delivery errors](https://developers.google.com/workspace/gmail/api/guides/handle-errors)

Limit concurrency and budget per mailbox and project. Respect backoff, provider retry timing and
daily sending limits independently. As checked on 2026-10-21, new-project defaults are 6,000 quota
units/minute/user/project and 1,200,000/minute/project; sending costs 100 units. Some older projects
retain prior quotas. Read the actual project's allocation rather than baking those numbers into
the application contract. [Current API quotas](https://developers.google.com/workspace/gmail/api/reference/quota)

## Privacy and maintenance

Render bounded plain text from untrusted MIME/HTML without fetching remote images. Treat `From`,
`Reply-To`, quoted instructions and authentication headers as attributed evidence, never Ward
identity. A sender can request an action but cannot grant private-record access or change the
recipient policy. Attachment parsing/download is a later explicit artifact/quarantine path.

Disclose any hosted model transfer and admit it under the user's purpose and privacy policy.
Workspace data cannot become general model-training material; current provider policy also
requires prompt-injection protection. [Workspace data policy](https://developers.google.com/workspace/workspace-api-user-data-developer-policy)

Routine releases retain the client/grant/cursor/outbox identities. Scope or material consent-screen
changes may require new authorization or verification; automatic refresh and watch renewal belong
to the service. [Approved-app changes](https://support.google.com/cloud/answer/13464018)

[Accounts and updates](accounts.md) · [Acceptance and delivery](delivery.md)
