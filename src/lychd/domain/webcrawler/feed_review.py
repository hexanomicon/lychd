"""New feed-only review producer; historical page reviews keep their original encoding."""

from __future__ import annotations

from lychd.domain.codex.schemas import NativeConsentBinding
from lychd.domain.scout.attempts import ScoutFeedPreparation, document_digest
from lychd.domain.web.consent_reviews import NativeReviewDocument, ReviewFact


def feed_review(
    preparation: ScoutFeedPreparation, *, legacy: bool = False
) -> tuple[NativeConsentBinding, NativeReviewDocument]:
    """Disclose fixed acquisition and application custody without copying seed or items."""
    if type(preparation) is not ScoutFeedPreparation:
        message = "Webcrawler feed review preparation differs."
        raise ValueError(message)
    p, c = preparation, preparation.consumer
    display_name = "Scout" if legacy else "Webcrawler"
    owner = display_name.lower()
    facts = (
        ("url", "Complete declared public feed URL", p.url),
        (
            "classification",
            "Classification basis",
            "Authenticated operator assertion of a public web locator; not a technical proof of publicness.",
        ),
        ("subject", "Local operator", p.subject),
        ("authentication", "Authentication generation", str(p.authentication_generation)),
        ("run", "Run", str(p.run_id)),
        ("request", "Acquisition request", str(p.request_id)),
        ("provider", "Native acquisition", f"{p.provider_id} / {p.profile}"),
        (
            "consumer",
            "Receiving application",
            f"{c.composition}@{c.composition_revision} / {c.pattern}@{c.pattern_revision}",
        ),
        ("admission", "Application admission", str(c.application_admission_id)),
        ("request_binding", "Application request digest", c.application_request_digest),
        ("seed_binding", "Complete retained campaign seed digest", c.seed_digest),
        ("filter_binding", "Initial retained local filter digest", c.initial_filter_digest),
        ("projection", "Observation and custody profiles", f"{c.observation_profile} / {c.projection} / {c.retention}"),
        (
            "dns",
            "DNS recipient",
            f"TCP resolver {p.resolver_address}:{p.resolver_port}; exact hostname A and AAAA questions.",
        ),
        ("custody", "Operator-declared resolver custody", p.resolver_custody_statement),
        (
            "disclosure",
            "Website disclosure",
            "TLS exposes the feed hostname as SNI. HTTPS sends the exact path and query to the certificate-verified, pinned public peer. The campaign seed and filter are not sent.",
        ),
        (
            "redirects",
            "Redirects and retries",
            "One exact feed; no redirect, automatic retry, provider fallback, item fetch, browser rendering, script, cookie or subresource.",
        ),
        (
            "limits",
            "Reserved network ceilings",
            f"Connects: {p.allowance.connects}; handoffs: {p.allowance.transmissions}; outbound payload bytes: {p.allowance.wire_bytes}. One 30-second acquisition deadline; response wire body at most 2 MiB, decoded UTF-8 RSS/XML at most 1 MiB.",
        ),
        (
            "extraction",
            "Extraction",
            "Fixed network-denied RSS worker; at most 100 item occurrences. Publisher data stays untrusted. Item links are inert data and grant no further contact.",
        ),
        (
            "local_use",
            "Local use",
            "Whole source-order title/link field, exact-locator duplicate grouping and literal case-folded local filtering only. No ranking, suitability, seller judgment, messaging, purchase, learning or recurring watching.",
        ),
        ("model", "Model demand", "No model call, capability grant or Dispatcher lease."),
        (
            "retention",
            "Application content retention",
            "Scavenger retains the complete seed (at most 16 KiB) and whole title/link field plus attribution (at most 256 KiB) until explicit authorized deletion after acquisition/result are terminal. Titles and links may contain personal data. Body, channel, summaries, publisher IDs/dates and separate contacts are not retained in that field.",
        ),
        (
            "receipts",
            "Execution metadata retention",
            f"Run/Graph/review retain references and digests, not a copied seed/filter or item values. {display_name} retains contact attribution and positively selected extraction metadata. Deletion leaves a content-free tombstone and necessary immutable receipts; it neither resets accounting nor implies backup erasure.",
        ),
        (
            "recovery",
            "Recovery and local reads",
            "After claim, lost material is unavailable and is never refetched from a receipt. Committed data permits only fresh authorized local reads/filters; new acquisition needs a fresh explicit request and consent. Deleted data is not an empty market and cannot be recreated by replay.",
        ),
        ("expiry", "Review and effect expiry", p.expires_at.isoformat()),
        (
            "withdrawal",
            "Withdraw approval",
            f"Cancel the Run or revoke the current {display_name} policy. This stops future handoffs and cannot retract bytes already accepted by the kernel. Deletion is a separate application operation after terminal disposition.",
        ),
    )
    document = NativeReviewDocument(
        title="Observe one public feed into a finite Scavenger title/link field",
        facts=tuple(ReviewFact(key=key, label=label, value=value) for key, label, value in facts),
    )
    binding = NativeConsentBinding(
        owner=owner,
        action_id=str(p.attempt_id),
        preparation_digest=p.digest,
        review_profile=f"{owner}.public-feed",
        review_profile_revision="1",
        review_producer=f"{owner}.public-feed-review",
        review_producer_revision="1",
        audience_digest=document_digest(
            {
                "subject": p.subject,
                "authentication_generation": str(p.authentication_generation),
                "purpose": p.purpose,
                "consumer_digest": c.digest,
            }
        ),
        review_digest=document.digest,
    )
    return binding, document
