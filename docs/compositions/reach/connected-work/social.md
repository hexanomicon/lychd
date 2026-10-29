---
title: Social accounts and advertising
icon: material/account-network
---

# Social accounts and advertising

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
| Facebook | A Page post as the configured Page with eligible tasks and `pages_manage_posts`. | A Page token does not supply ordinary personal-profile publishing. [Page posts](https://developers.facebook.com/documentation/pages-api/posts). |
| LinkedIn | Member publishing with `w_member_social`; organization publishing with `w_organization_social` and an eligible organization role. | Organization Community Management access requires its own approval; member sharing does not grant organization or advertising access. [Getting access](https://learn.microsoft.com/en-us/linkedin/shared/authentication/getting-access), [Posts API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api?view=li-lms-2026-10). |
| X | Original public posts with user-delegated OAuth. | App-only bearer access does not authorize posting as a person. Automatic replies and private DMs are different operations. [OAuth](https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code), [Create Posts](https://docs.x.com/x-api/posts/create-post). |

[Email](../email.md), [Chat](../chat.md) and [Forge](../forge.md) own the other provider-family routes.
This assessment stays with the [Social](../social.md) post contract and its advertising boundary.

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

The social subset pins Meta Graph `v26.0` and LinkedIn `202610` with Rest.li `2.0.0`.
Those pins need maintenance and qualification before live transport; they are not a promise of
permanent provider compatibility.
[Page posts](https://developers.facebook.com/documentation/pages-api/posts),
[LinkedIn posts](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api?view=li-lms-2026-10)

No builder retries, rotates accounts, fetches a link, opens a session or sends a request. A future
transport must check current authority, exact destination, provider limits and eligibility,
persist its attempt before submission, and distinguish rejected, accepted and unknown results.
Provider acceptance cannot manufacture exactly-once delivery. A timeout after submission must
not turn WUPHF into another send to every destination.

[Social](../social.md) · [Preparation and user stories](preparation.md) · [Account lifecycle](accounts.md) · [Delivery gates](delivery.md)
