---
title: Accounts, social publishing and advertising
icon: material/account-network
---

# Accounts, social publishing and advertising

A founder wants to describe their AI service on Facebook and LinkedIn, answer interested people,
and eventually pay to distribute a campaign. Those are different operations with different account
and provider permissions. Prepare the content and exact author first; an ordinary publication
grant cannot silently become authority to spend money.

The following official-source assessment was checked **2026-10-29**. The
[connected preparation profile](preparation.md) implements local request construction. Account
onboarding, API access approval and live publication remain separate qualification work.

## Pick the account and the operation

| Service | Supported direction | What account access does not imply |
| --- | --- | --- |
| Gmail | Owner-authorized Gmail REST; personal Gmail or Workspace. | A Workspace subscription does not verify a public app or grant access to other mailboxes. See the [Gmail profile](gmail.md). |
| Fastmail | JMAP for mail and submission; own-use API token or registered OAuth application. | Basic plans do not supply API tokens. Email submission access also needs Email access; broad provider permissions must remain locally restricted. [Developer entry](https://www.fastmail.com/dev/), [token eligibility](https://www.fastmail.help/hc/en-us/articles/5254602856719-API-tokens). |
| Telegram | A bot's admitted chats through Bot API. | A bot cannot initiate arbitrary user chats. Bot privacy mode and group permissions affect what it sees. Personal MTProto login is a separate user session, not a bot token. [Bots](https://core.telegram.org/bots), [user authorization](https://core.telegram.org/api/auth). |
| WhatsApp | Business Platform phone and permitted recipients. | No generic OAuth access to existing personal chats. General-purpose AI, business support and the limited owner–agent platform have distinct conditions. See the [WhatsApp assessment](whatsapp.md). |
| Discord | The existing bot/operator profile and its admitted guild/channel boundary. | An ordinary user's session is not a bot installation or an authority shortcut. See the [operator profile](../operator.md). |
| GitHub | Selected-repository GitHub App installation for issue/PR timeline correspondence. | Code changes, formal approving reviews, merges and workflow execution remain separate. See the [GitHub profile](github.md). |
| Facebook | A Page post as the configured Page with eligible tasks and `pages_manage_posts`. | A Page token does not supply ordinary personal-profile publishing. [Page posts](https://developers.facebook.com/documentation/pages-api/posts). |
| LinkedIn | Member publishing with `w_member_social`; organization publishing with `w_organization_social` and an eligible organization role. | Organization Community Management access requires its own approval; member sharing does not grant organization or advertising access. [Getting access](https://learn.microsoft.com/en-us/linkedin/shared/authentication/getting-access), [Posts API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api?view=li-lms-2026-10). |
| X | Original public posts with user-delegated OAuth. | App-only bearer access does not authorize posting as a person. Automatic replies and private DMs are different operations. [OAuth](https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code), [Create Posts](https://docs.x.com/x-api/posts/create-post). |
| Radicle | A later Forge profile with node/key, repository RID and issue/patch object identities. | It is not a GitHub host substitution or OAuth installation. Local acceptance and peer replication are different receipts. No write adapter is qualified here. [User guide](https://radicle.dev/guides/user). |

Fastmail preparation uses JMAP `Email/query`/`Email/get` and explicit `Email/set` followed by
`EmailSubmission/set`. It binds a submission identity and SMTP envelope separately from message
headers. The credential owner must discover and validate the Session's capabilities and API URL.
An HTTP 200 can contain method-level errors; submission acceptance would still not prove final
recipient delivery. [JMAP Mail](https://www.rfc-editor.org/rfc/rfc8621.html)

Telegram's current terms restrict AI use of obtained content. The documented exception requires
explicit, informed, affirmative and continued consent from all relevant users for the specific
content and context. One owner's consent cannot admit everyone else's personal chat history.
These conditions also matter before bot-context ingestion into a model; local request construction
does not satisfy them. [API terms](https://core.telegram.org/api/terms),
[content licensing](https://telegram.org/tos/content-licensing)

X requires prior written explicit approval for an AI reply bot. Its automation policy also
restricts unsolicited automated replies/DMs and requires a working opt-out. This profile prepares
original posts; it does not establish that approval or provide a reply bot. Prepared AI-authored
posts include the API's `made_with_ai` field. [Automation rules](https://help.x.com/en/rules-and-policies/x-automation),
[post request](https://docs.x.com/x-api/posts/create-post)

## Promotional content before paid distribution

LinkedIn commentary uses its `little` markup syntax. The builder escapes reserved characters to
preserve literal input, and conservatively caps the encoded commentary at 3,000 UTF-16 units.
It refuses excess text rather than splitting one reviewed post into several effects.
[Text syntax](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/little-text-format?view=li-lms-2026-10),
[post length](https://www.linkedin.com/help/lms/answer/a522483/differences-between-posting-updates-and-publishing-articles?lang=en)

The first founder journey is: accept the service's claims and creative assets, prepare one
Facebook Page post and one LinkedIn post, review their exact author/text/audience, then admit each
publication separately through a future qualified delivery path. Cross-posting is a new disclosure
at each destination. A post's provider acceptance does not prove reach, engagement or a sale.

Images and video require separately admitted upload artifacts and returned media references;
the present connector subset constructs text requests. It does not scrape link previews, generate
assets, upload media or boost a post. [Broadcast release](../../broadcast/release.md) retains
editorial acceptance, claims, credits, disclosures and publication judgment.

Paid campaigns need a separately reviewed request binding at least:

- The advertiser, platform, ad account, campaign objective and permitted product.
- Exact accepted creative, destination URL, audience and targeting constraints.
- Currency, daily or lifetime budget, bid constraints, start/end and total spend ceiling.
- Draft versus activation, current account role, provider policy eligibility and review identity.
- Per-operation receipt, unknown-state reconciliation, and an independently admitted pause action.

This is a design boundary, not a delivered advertising request type or campaign executor.
Do not infer activation authority from approval of the copy, a Page role, or a successful upload.

Meta's Marketing API uses `ads_read` and `ads_management` for the corresponding operations.
Own-account versus other-account access differs. Limited/Full Marketing API tiers are separate
from Standard/Advanced permission access, and development-tier calls still touch production
data. [Marketing authorization](https://developers.facebook.com/documentation/ads-commerce/marketing-api/get-started/authorization)

LinkedIn Advertising requires separate access approval and appropriate ad-account roles. Its
development tier permits edits to up to five administered ad accounts. Version `202610` adds
member/organization boost scopes, which do not follow from ordinary posting. Never silently
upgrade an organic post into a charged boost. [Access tiers and permissions](https://learn.microsoft.com/en-us/linkedin/marketing/increasing-access?view=li-lms-2026-10)

## Protocol changes and recovery

The prepared subset pins explicit provider versions where required: GitHub REST `2026-03-10`,
Meta Graph `v26.0`, and LinkedIn `202610` with Rest.li `2.0.0`. Those pins need maintenance and
qualification before live transport; they are not a promise of permanent provider compatibility.
[GitHub comment API](https://docs.github.com/en/rest/issues/comments),
[Page posts](https://developers.facebook.com/documentation/pages-api/posts),
[LinkedIn posts](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api?view=li-lms-2026-10)

No builder retries, rotates accounts, fetches a link, opens a session or sends a request. A future
transport must check current authority, exact destination, provider limits and eligibility,
persist its attempt before submission, and distinguish rejected, accepted and unknown results.
Provider acceptance cannot manufacture exactly-once delivery. A timeout after submission must
not turn WUPHF into another send to every destination.

[Preparation and user stories](preparation.md) · [Account lifecycle](accounts.md) · [Delivery gates](delivery.md)
