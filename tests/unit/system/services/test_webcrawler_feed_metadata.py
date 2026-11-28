"""Positive metadata projection, not acquisition, actual custody or settlement proof."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any

import pytest

from lychd.domain.scout.extraction import (
    ExtractedFeed,
    ExtractedText,
    ExtractionCode,
    ExtractionError,
    FeedChannel,
    FeedItem,
)
from lychd.system.scout_worker import RSS_STRATEGY, RSS_TRANSFORMATIONS
from lychd.system.services.webcrawler_workflow import extraction_metadata
from tests.webcrawler_fixtures import webcrawler_material


def fixture() -> ExtractedFeed:
    return ExtractedFeed(
        media_type="text/xml",
        channel=FeedChannel("channel-secret", "https://example.com/channel-secret", "channel-summary-secret"),
        items=(
            FeedItem("title-secret", "https://example.com/item-secret", "summary-secret", "date-secret", "id-secret"),
        ),
        omitted_elements=3,
        source_digest="a" * 64,
        record_digest="b" * 64,
        strategy=RSS_STRATEGY,
        transformations=RSS_TRANSFORMATIONS,
    )


def test_feed_receipt_projection_has_exact_metadata_keys_and_no_item_or_channel_values() -> None:
    metadata = extraction_metadata(fixture())
    assert metadata == {
        "media_type": "text/xml",
        "source_digest": "a" * 64,
        "record_digest": "b" * 64,
        "strategy": RSS_STRATEGY,
        "transformations": RSS_TRANSFORMATIONS,
        "extractor": "scout-rss-extract@1",
        "item_count": 1,
        "omitted_elements": 3,
    }
    encoded = json.dumps(metadata)
    for marker in (
        "channel-secret",
        "channel-summary-secret",
        "title-secret",
        "item-secret",
        "summary-secret",
        "date-secret",
        "id-secret",
    ):
        assert marker not in encoded


def test_legacy_static_metadata_keeps_its_existing_exact_values_without_text() -> None:
    text = webcrawler_material().extraction
    assert extraction_metadata(text) == {
        "media_type": "text/plain",
        "source_digest": "4" * 64,
        "record_digest": "5" * 64,
        "text_digest": "6" * 64,
        "strategy": "plain-text@1",
        "transformations": ("strict-utf8",),
        "extractor": "scout-static-extract@1",
    }
    assert text.text not in json.dumps(extraction_metadata(text))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("strategy", "source-authored-secret"),
        ("transformations", ("secret",)),
        ("extractor", "unknown"),
        ("media_type", "text/html"),
        ("omitted_elements", True),
        ("omitted_elements", 10001),
        ("source_digest", "source-authored-secret"),
        ("record_digest", "0" * 65),
    ],
)
def test_unknown_feed_metadata_refuses_with_content_free_reason(field: str, value: Any) -> None:
    with pytest.raises(ExtractionError) as error:
        extraction_metadata(replace(fixture(), **{field: value}))
    assert error.value.code is ExtractionCode.PROTOCOL
    assert "source-authored-secret" not in str(error.value)


def test_widened_producer_type_cannot_implicitly_add_future_receipt_fields() -> None:
    @dataclass(frozen=True)
    class WidenedText(ExtractedText):
        extra: str = "new-source-content"

    text = webcrawler_material().extraction
    widened = WidenedText(
        media_type=text.media_type,
        text=text.text,
        source_digest=text.source_digest,
        record_digest=text.record_digest,
        text_digest=text.text_digest,
        strategy=text.strategy,
        transformations=text.transformations,
    )
    with pytest.raises(ExtractionError) as error:
        extraction_metadata(widened)
    assert error.value.code is ExtractionCode.PROTOCOL
    assert "new-source-content" not in str(error.value)
