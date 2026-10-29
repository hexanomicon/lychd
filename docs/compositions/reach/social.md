---
title: Social
icon: material/post-outline
---

# Social

Prepare public launch copy for the founder's account or company Page. Social shares the intent
to publish an original organic text post while preserving each provider's author and payload.

`SocialTarget` selects a connection, external `account_id`, `actor_kind` and visibility. The
account must equal the connection's declared publishing actor; `ConnectedPolicy` selects its
exact allowed target. The current builders admit public posts only.

| Provider | Actor | Request-specific behavior |
| --- | --- | --- |
| Facebook | Page. | Page-feed text post; personal-profile mode refuses. |
| LinkedIn | Member/person or organization with its matching URN. | Literal text escapes the provider's `little` markup and obeys a conservative encoded-text limit. |
| X | User. | Original text post with the prepared AI-authorship field; no automatic reply bot. |

The [social account and advertising assessment](connected-work/social.md) owns access requirements,
provider versions and the founder's promotional journey. Social reads, replies, DMs, media uploads,
boosts, advertising campaigns and spending are outside the prepared operation set.

[Broadcast](../broadcast/release.md) owns editorial acceptance and publication judgment. Settled,
approved copy can enter Reach as input; coordinating several live Composition Invocations needs
a [Suite](../products-and-suites.md#compositions-relate-without-nesting).

Use [connected preparation](connected-work/preparation.md) for the founder launch example and
native serial Graph. A prepared post does not authenticate its author or authorize publication.

[Reach](index.md)
