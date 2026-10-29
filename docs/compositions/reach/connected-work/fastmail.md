---
title: Fastmail connection
icon: material/email-outline
---

# Fastmail connection

The founder keeps company mail in Fastmail and prepares a client reply through the same
[Email](../email.md) request used for Gmail. The Fastmail builder translates it into JMAP;
mail identity and the submission envelope remain explicit.

This page describes Fastmail request preparation in `reach.connect.prepare@1`. The
[connected-work study](index.md) retains the proposed account lifecycle and durable delivery
contract; the builder does not connect an account or create a remote draft.

## Select the protocol account and sender

| Value | Meaning |
| --- | --- |
| `Connection.account_id` and `EmailTarget.mailbox_id` | The same selected JMAP mail account ID. This is not a folder ID. |
| `Connection.actor_id` and `EmailTarget.sender` | The same declared sender address. An address alone proves no sending grant. |
| `identity_id` | The explicit JMAP sending identity required for submission. |
| `draft_mailbox_id` | The separate mailbox in which the exact new email is created. Required for sends. |
| To/Cc/Bcc | Frozen message recipients, also bound into the explicit SMTP envelope. |

## Prepare the read or submission

A read prepares bounded `Email/query` followed by `Email/get` using the query's ID result.
The selected projection contains IDs, addresses, subject, preview and receipt time; it does not
fetch full bodies or attachments. A cursor supplies the next numeric query position.

A send prepares `Email/set` to create the exact content, then `EmailSubmission/set` with the
creation reference, selected identity and complete recipient envelope. It does not submit an
existing mutable draft by ID. RFC reply references are supported; assigning a thread or preparing
a thread-scoped read refuses. A repeated preparation is not permission to repeat either write.

The route `fastmail:api` is a semantic selector. A later credential owner must obtain and validate
the authenticated JMAP Session, API URL, account and required mail/submission capabilities.
HTTP 200 can contain method-level errors, and submission acceptance would not prove recipient
delivery. [JMAP Mail](https://www.rfc-editor.org/rfc/rfc8621.html)

Own-use API tokens and registered OAuth applications are different onboarding roads. API tokens
are unavailable on Basic plans; submission access also requires Email access. Those provider
grants do not waive Reach's local restrictions.
[Fastmail developers](https://www.fastmail.com/dev/) ·
[API tokens](https://www.fastmail.help/hc/en-us/articles/5254602856719-API-tokens)

Use the `founder-policy.json` and `founder-launch.json` fixtures described in
[connected preparation](preparation.md) to inspect the JMAP plan without credentials.

[Email](../email.md) · [Accounts](accounts.md) · [Delivery gates](delivery.md)
