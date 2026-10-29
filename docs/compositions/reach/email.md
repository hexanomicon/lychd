---
title: Email
icon: material/email-outline
---

# Email

Reply to a client from the selected mailbox without changing the application flow when the
provider changes. Email owns the request's mail semantics: sender, recipients, subject, content
and reply references. Gmail and Fastmail translate that request into different protocols.

`EmailTarget` names a local connection, a protocol account selector, the sender and exact
To/Cc/Bcc recipients. `ConnectedPolicy` selects the connection and allowed targets, operations
and limits. The connection's external account declaration does not authenticate a mailbox.

| Provider | Account selection | Prepared read | Prepared send |
| --- | --- | --- | --- |
| [Gmail](connected-work/gmail.md) | `mailbox_id = "me"`; the declared immutable Google subject remains separate. | Bounded message-ID listing, without message bodies. | Canonical RFC MIME encoded as base64url, with optional thread and reply headers. |
| [Fastmail](connected-work/fastmail.md) | `mailbox_id` is the selected JMAP account ID, not a mailbox folder. | Bounded query/get header and preview projection. | Exact email creation followed by submission with its sending identity, draft mailbox and SMTP envelope. |

`MailRequestBuilder` has two concrete implementations, `GmailRequestBuilder` and
`FastmailRequestBuilder`. Callers prepare a read or send; each implementation retains its own
identifiers, output and refusal rules. Thread-scoped reads refuse rather than widening into an
unrelated mailbox listing. JMAP does not acquire a Gmail-shaped MIME transport.

[Connected preparation](connected-work/preparation.md) shows the shared native Graph and a finite
WUPHF announcement. Its result contains application bytes and a provider route selector, with no
account authentication or send authority. [Accounts](connected-work/accounts.md) and
[delivery](connected-work/delivery.md) retain the later connected-operation contract.

[Reach](index.md)
