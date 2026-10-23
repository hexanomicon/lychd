---
title: GitHub connection
icon: fontawesome/brands/github
---

# :fontawesome-brands-github: GitHub connection

The repository owner installs Reach on selected repositories. An admitted issue or pull-request
conversation can produce a proposed timeline comment, then one delivery as the application's bot.
The conversation can ask for a code change without granting permission to execute or publish one.

The candidate `reach.github.correspondence@1` profile belongs to the [successor study](index.md).
It starts with GitHub.com; another GitHub host/version needs its own pinned compatibility and
credential configuration, not an arbitrary model-selected API URL.

## Application and permissions

Prefer a **GitHub App** with installation identity and selected-repository access. OAuth Apps bind
more broadly to user authority. Acting as a human is a separate optional authorization mode,
not implied by bot installation. [App comparison](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/differences-between-github-apps-and-oauth-apps)

Propose Issues write and Pull requests read, with no Contents, Workflows, Checks, Commit statuses,
Administration or organization permission. Issue-comment REST endpoints cover issue and PR timeline
comments, while `issue_comment` webhooks specifically need Issues read. These permission families
are broader than this profile: the local operation allowlist admits only bounded reads and comment
creation/updates to Reach-owned comments. Issue state changes remain excluded.
[Comment endpoints](https://docs.github.com/en/rest/issues/comments),
[webhook permissions](https://docs.github.com/en/webhooks/webhook-events-and-payloads#issue_comment)

Installation tokens expire after **one hour** and can be narrowed to fewer repositories and
permissions. Mint them on demand inside the credential owner. A publisher's app signing key can
reach multiple installations and never belongs in customer software. The first self-hosted road
uses a customer-owned app; a [manifest registration](https://docs.github.com/en/apps/sharing-github-apps/registering-a-github-app-from-a-manifest)
can reduce manual setup. [Installation tokens](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app)

## Events and missed work

An initial request is either operator-originated or a first-line `/reach ask` text marker from a
configured external actor in an admitted conversation. This is Reach's parser convention, not a
native GitHub slash-command facility or local authority proof. Ignore the app's own comments,
bot/automation authors by default, unconfigured actors and untriggered new activity before
cognition. Resource changes may refresh a bounded projection without creating a request.

An edit to a triggering comment invalidates any unsent preparation based on the old version.
It does not revise or resend an accepted reply. A new reply to an edited request needs a separately
admitted request/version under explicit policy; polling overlap alone cannot create that authority.

The first road polls admitted repositories/conversations with pagination, overlap windows and
conditional requests. Persist provider object id, version/update time and processed cursor; dedupe
overlaps and distinguish edits from a new request. A changed comment cannot silently revise an
already-approved response. Polling recovers accessible current state, not every deleted or
intermediate event. [Comment polling](https://docs.github.com/en/rest/issues/comments#list-issue-comments-for-a-repository),
[conditional requests](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api)

A later webhook profile verifies HMAC-SHA256 over the original body, binds the configured
app/installation/repository and event/action, then durably admits intake before returning 2xx
within the provider deadline. Deduplicate `X-GitHub-Delivery` with a payload fingerprint and bind
each semantic action to its resource version as well; the same GUID is retained on redelivery.
Provider signature proves source bytes, not Ward authority for the commenter.
[Signature validation](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries),
[webhook intake](https://docs.github.com/en/webhooks/using-webhooks/best-practices-for-using-webhooks)

GitHub does not automatically redeliver failed webhooks, and requested redelivery is limited to
three days. App-wide delivery inspection/redelivery needs app-JWT custody rather than an ordinary
installation token. A publisher-operated service must own that repair loop; resource polling
remains the bounded reconciliation path. [Failure handling](https://docs.github.com/en/webhooks/using-webhooks/handling-failed-webhook-deliveries),
[redelivery](https://docs.github.com/en/webhooks/testing-and-troubleshooting-webhooks/redelivering-webhooks),
[app delivery API](https://docs.github.com/en/rest/apps/webhooks)

## Comment delivery and wider capabilities

Freeze host, installation, repository id, issue/PR id, body, visibility observation and actor before
review or standing policy. Check current installation access and destination again at send time.
For reconciliation, a proposed opaque Reach marker in a hidden Markdown comment can bind a
delivery occurrence to the bot-authored comment. It is externally visible source metadata, must
be included in the admitted bytes, and must contain no customer/private identifier.

A marker, GraphQL `clientMutationId`, or check-run `external_id` does not establish provider-enforced
uniqueness. After an ambiguous POST, inspect the intended thread for matching bot, marker and body;
retain the returned provider id/URL when known. Inconclusive reads preserve `UNKNOWN`, not a safe
resend. Updating a known comment remains another separately authorized exact edit.

PR diff comments and formal reviews have separate APIs and Pull requests write. `APPROVE` and
`REQUEST_CHANGES` are consequential review actions, not ordinary replies. Discussions use GraphQL
and need a separate compatibility probe. Checks/statuses express commit-specific results and
require their own permissions and judgment owner. Code edits, merges, releases and workflow runs
belong to the relevant software-change owner, not this communications profile.
[Reviews](https://docs.github.com/en/rest/pulls/reviews),
[Discussions](https://docs.github.com/en/graphql/guides/using-the-graphql-api-for-discussions)

REST installation allowance commonly starts at 5,000 requests/hour and varies with installation
and plan. Respect primary response headers and secondary limits, serialize/pause content writes,
and honor `Retry-After` and reset times on 403/429. No account/key rotation bypass.
[Rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)

Ordinary releases preserve the app installation. Additional permissions require the installation
owner's approval; an installation that has not approved keeps its old grant. Repository removal,
installation suspension or uninstall fences pending sends without rerouting them.
[Permission changes](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app#about-changes-to-permissions)

[Accounts and updates](accounts.md) · [Acceptance and delivery](delivery.md)
