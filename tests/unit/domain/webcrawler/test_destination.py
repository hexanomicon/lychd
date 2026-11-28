from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from typing import NoReturn, cast

import pytest

from lychd.domain.scout.destination import (
    DestinationCode,
    DestinationError,
    classify_destination_addresses,
    preflight_destination,
)


@pytest.mark.parametrize("suffix", ["", "/", "?", "/?", "/a//../b%2fC?q=a+b&q=%2F&x=", "?https://other.test/x"])
def test_preserves_path_and_query_while_normalizing_only_authority(suffix: str) -> None:
    original = f"https://ExAmPlE.COM:443{suffix}"
    candidate = preflight_destination(original)
    assert candidate.original_url == original
    assert candidate.normalized_url == f"https://example.com{suffix}"
    assert candidate.hostname == "example.com"
    assert candidate.ip_literal is None
    assert candidate.profile == "public-https-destination@1"


@pytest.mark.parametrize("host", ["8.8.8.8", "[2606:4700:4700::1111]", "xn--bcher-kva.example", "a-b.example"])
def test_accepts_canonical_public_literals_and_ascii_dns(host: str) -> None:
    assert preflight_destination(f"https://{host}:443/").normalized_url == f"https://{host}/"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "HTTPS://example.com",
        "//example.com",
        "https:///example.com",
        "https://",
        "https://example.com#",
        "https://example.com/#fragment",
        "https://user:secret@example.com",
        "https://example.com@127.0.0.1",
        "https://example.com%2f.evil",
        "https://%65xample.com",
        "https://example.com:80",
        "https://example.com:",
        "https://example.com:0443",
        "https://example.com:+443",
        "https://example.com.",
        "https://.example.com",
        "https://a..example",
        "https://localhost",
        "https://-bad.example",
        "https://bad-.example",
        "https://bad_name.example",
        "https://bücher.example",
        "https://127.1",
        "https://0177.0.0.1",
        "https://2130706433",
        "https://0x7f000001",
        "https://0x7f.0.0.1",
        "https://0x8.0x8.0x8.0x8",
        "https://1.2.3.0x4",
        "https://2606:4700:4700::1111",
        "https://[2606:4700:4700:0:0:0:0:1111]",
        "https://[2606:4700:ABCD::1]",
        "https://[fe80::1%25eth0]",
        "https://[8.8.8.8]",
        "https://example.com\\@evil.example",
        "https://example.com/%",
        "https://example.com/%0",
        "https://example.com/%GG",
    ],
)
def test_refuses_ambiguous_or_out_of_profile_url(url: str) -> None:
    with pytest.raises(DestinationError):
        preflight_destination(url)


@pytest.mark.parametrize("char", [chr(value) for value in range(33)] + ["\x7f", "\x80", "\u00a0"])
@pytest.mark.parametrize("position", ["before", "host", "path"])
def test_refuses_controls_and_whitespace_before_any_parser_repair(char: str, position: str) -> None:
    url = {
        "before": f"{char}https://example.com",
        "host": f"https://exam{char}ple.com",
        "path": f"https://example.com/{char}",
    }[position]
    with pytest.raises(DestinationError) as failure:
        preflight_destination(url)
    assert failure.value.code is DestinationCode.URL


def test_url_limit_is_inclusive() -> None:
    url = "https://example.com/".ljust(4096, "x")
    assert preflight_destination(url).normalized_url == url
    with pytest.raises(DestinationError) as failure:
        preflight_destination(url + "x")
    assert failure.value.code is DestinationCode.URL_LIMIT


@pytest.mark.parametrize("url", [None, b"https://example.com", 123])
def test_refuses_non_string_input(url: object) -> None:
    with pytest.raises(DestinationError) as failure:
        preflight_destination(cast("str", url))
    assert failure.value.code is DestinationCode.URL


def test_refuses_string_subclass_before_observing_its_contents() -> None:
    class MisleadingString(str):
        __slots__ = ()

        def __len__(self) -> int:
            return 5000

    with pytest.raises(DestinationError) as failure:
        preflight_destination(MisleadingString("https://example.com"))
    assert failure.value.code is DestinationCode.URL


def test_accepts_maximum_dns_name_and_label_lengths() -> None:
    host = ".".join(["a" * 63, "b" * 63, "c" * 63, "d" * 61])
    assert len(host) == 253
    assert preflight_destination(f"https://{host}").hostname == host


@pytest.mark.parametrize("host", ["a" * 64 + ".example", ".".join(["a" * 63] * 4)])
def test_refuses_overlong_dns_labels_and_names(host: str) -> None:
    with pytest.raises(DestinationError) as failure:
        preflight_destination(f"https://{host}")
    assert failure.value.code is DestinationCode.AUTHORITY


@pytest.mark.parametrize(
    "address",
    [
        "0.0.0.0",  # noqa: S104 - refusal fixture, never a socket binding
        "0.255.255.255",
        "10.1.2.3",
        "100.64.0.0",
        "100.127.255.255",
        "127.0.0.1",
        "169.254.169.254",
        "172.16.0.0",
        "172.31.255.255",
        "192.0.0.9",
        "192.0.2.1",
        "192.31.196.1",
        "192.52.193.1",
        "192.88.99.2",
        "192.168.1.1",
        "192.175.48.1",
        "198.18.0.0",
        "198.19.255.255",
        "198.51.100.1",
        "203.0.113.1",
        "224.0.0.0",
        "239.255.255.255",
        "240.0.0.0",
        "255.255.255.255",
        "168.63.129.16",
        "::",
        "::1",
        "::ffff:808:808",
        "64:ff9b::808:808",
        "100::1",
        "fc00::1",
        "fe80::1",
        "ff02::1",
        "2001::1",
        "2001:1ff:ffff::1",
        "2001:db8::1",
        "2002:808:808::1",
        "2620:4f:8000::1",
        "3ffe::1",
        "3fff::1",
        "3fff:fff::1",
        "4000::1",
        "5f00::1",
    ],
)
def test_refuses_forbidden_literals_and_mixed_answer_sets(address: str) -> None:
    host = f"[{address}]" if ":" in address else address
    with pytest.raises(DestinationError) as literal_failure:
        preflight_destination(f"https://{host}")
    assert literal_failure.value.code is DestinationCode.FORBIDDEN
    candidate = preflight_destination("https://example.com")
    with pytest.raises(DestinationError) as dns_failure:
        classify_destination_addresses(candidate, hostname="example.com", addresses=("8.8.8.8", address))
    assert dns_failure.value.code is DestinationCode.FORBIDDEN


def test_answer_order_and_both_families_survive_deduplication() -> None:
    candidate = preflight_destination("https://EXAMPLE.com")
    addresses = ("8.8.8.8", "2606:4700:4700::1111", "8.8.8.8", "1.1.1.1")
    result = classify_destination_addresses(candidate, hostname="example.com", addresses=addresses)
    assert result.candidate is candidate
    assert result.addresses == ("8.8.8.8", "2606:4700:4700::1111", "1.1.1.1")


@pytest.mark.parametrize(
    "address",
    [
        "100.63.255.255",
        "100.128.0.0",
        "172.15.255.255",
        "172.32.0.0",
        "198.17.255.255",
        "198.20.0.0",
        "2001:200::1",
        "2606:4700::1",
        "3fff:1000::1",
    ],
)
def test_accepts_ordinary_addresses_adjacent_to_excluded_ranges(address: str) -> None:
    result = classify_destination_addresses(
        preflight_destination("https://example.com"), hostname="example.com", addresses=(address,)
    )
    assert result.addresses == (address,)


def test_duplicate_answers_count_toward_limit_before_deduplication() -> None:
    candidate = preflight_destination("https://example.com")
    assert classify_destination_addresses(candidate, hostname="example.com", addresses=("8.8.8.8",) * 64).addresses == (
        "8.8.8.8",
    )
    with pytest.raises(DestinationError) as failure:
        classify_destination_addresses(candidate, hostname="example.com", addresses=("8.8.8.8",) * 65)
    assert failure.value.code is DestinationCode.ANSWERS


@pytest.mark.parametrize("hostname", ["EXAMPLE.com", "example.com.", "other.example", "example.com:443"])
def test_requires_exact_canonical_hostname_for_supplied_answers(hostname: str) -> None:
    with pytest.raises(DestinationError) as failure:
        classify_destination_addresses(
            preflight_destination("https://example.com"), hostname=hostname, addresses=("8.8.8.8",)
        )
    assert failure.value.code is DestinationCode.HOST_MISMATCH


@pytest.mark.parametrize("addresses", [(), ["8.8.8.8"], None, "8.8.8.8"])
def test_refuses_incomplete_or_non_tuple_answer_input(addresses: object) -> None:
    with pytest.raises(DestinationError) as failure:
        classify_destination_addresses(
            preflight_destination("https://example.com"),
            hostname="example.com",
            addresses=cast("tuple[str, ...]", addresses),
        )
    assert failure.value.code is DestinationCode.ANSWERS


@pytest.mark.parametrize(
    "address",
    [
        "8.8.8.8 ",
        "008.8.8.8",
        "0x08080808",
        "8.8.8",
        "[2606:4700::1]",
        "2606:4700:0:0:0:0:0:1",
        "2606:4700::ABCD",
        "2606:4700::1%eth0",
        "not-an-address",
        None,
        134744072,
    ],
)
def test_refuses_malformed_or_noncanonical_supplied_addresses(address: object) -> None:
    with pytest.raises(DestinationError) as failure:
        classify_destination_addresses(
            preflight_destination("https://example.com"), hostname="example.com", addresses=(cast("str", address),)
        )
    assert failure.value.code is DestinationCode.ADDRESS


@pytest.mark.parametrize("address", ["8.8.8.8", "2606:4700:4700::1111"])
def test_literal_requires_exact_supplied_address(address: str) -> None:
    host = f"[{address}]" if ":" in address else address
    candidate = preflight_destination(f"https://{host}")
    assert classify_destination_addresses(candidate, hostname=address, addresses=(address,)).addresses == (address,)
    with pytest.raises(DestinationError) as failure:
        classify_destination_addresses(candidate, hostname=address, addresses=(address, "1.1.1.1"))
    assert failure.value.code is DestinationCode.LITERAL_MISMATCH


def test_revalidates_caller_constructed_candidate_facts() -> None:
    candidate = replace(preflight_destination("https://example.com"), hostname="different.example")
    with pytest.raises(DestinationError) as failure:
        classify_destination_addresses(candidate, hostname="different.example", addresses=("8.8.8.8",))
    assert failure.value.code is DestinationCode.CANDIDATE


def test_facts_are_immutable_and_refusals_do_not_expose_input() -> None:
    candidate = preflight_destination("https://secret.example/private?token=secret")
    result = classify_destination_addresses(candidate, hostname="secret.example", addresses=("8.8.8.8",))
    for target, attribute, value in ((candidate, "hostname", "other.example"), (result, "addresses", ())):
        with pytest.raises(FrozenInstanceError):
            setattr(target, attribute, value)
    with pytest.raises(DestinationError) as failure:
        classify_destination_addresses(candidate, hostname="secret.example", addresses=("127.0.0.1",))
    assert "secret" not in str(failure.value)
    assert "127.0.0.1" not in str(failure.value)


def test_preflight_performs_no_io(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse_io(*args: object, **kwargs: object) -> NoReturn:
        pytest.fail("Destination preflight attempted I/O")

    with monkeypatch.context() as isolated:
        for target in (
            "builtins.open",
            "io.open",
            "os.open",
            "socket.socket",
            "socket.getaddrinfo",
            "subprocess.Popen",
        ):
            isolated.setattr(target, refuse_io)
        candidate = preflight_destination("https://example.com")
        result = classify_destination_addresses(candidate, hostname="example.com", addresses=("8.8.8.8",))
    assert result.addresses == ("8.8.8.8",)
