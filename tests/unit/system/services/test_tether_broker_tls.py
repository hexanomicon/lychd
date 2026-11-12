"""Controlled broker TLS assembly and cleanup, not live peer qualification."""

from __future__ import annotations

import asyncio
import socket
import ssl
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from unittest.mock import Mock

import pytest

from lychd.domain.scout.transport import FetchCode, FetchError, NetworkHandoff, NetworkTarget
from lychd.system.services import scout_socket

# This focused assembly test constructs the internal carrier without a broker socket.
from lychd.system.services.tether.connector import _BrokerStream as BrokerStream  # pyright: ignore[reportPrivateUsage]

TARGET = NetworkTarget("10.44.0.1", 8443, "peer.test", "origin")


class Gate:
    def handoff(self, handoff: NetworkHandoff, action: Callable[[], int]) -> int:
        del handoff
        return action()


@dataclass
class TLSHarness:
    """Substitute the raw socket and OpenSSL while retaining real TLS assembly."""

    raw: Mock
    context: Mock
    tls: Mock
    ca_file: Path


@pytest.fixture
def tls_harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TLSHarness:
    ca_file = tmp_path / "ca.pem"
    ca_file.write_text("fixture trust roots")
    context = Mock(spec=ssl.SSLContext)
    context.options = 0
    tls = Mock(spec=ssl.SSLObject)
    tls.selected_alpn_protocol.return_value = "http/1.1"
    context.wrap_bio.return_value = tls
    monkeypatch.setattr(scout_socket.ssl, "SSLContext", Mock(return_value=context))
    return TLSHarness(Mock(spec=socket.socket), context, tls, ca_file)


def carrier(raw: Mock, *, target: NetworkTarget = TARGET, lifetime: float = 5) -> BrokerStream:
    return BrokerStream(cast("socket.socket", raw), target, Gate(), time.monotonic() + lifetime)


@pytest.mark.asyncio
async def test_broker_tls_retains_application_hostname_and_exact_trust(tls_harness: TLSHarness) -> None:
    h = tls_harness
    stream = await carrier(h.raw).wrap_tls(ca_file=h.ca_file)
    assert isinstance(stream, scout_socket.PinnedTlsStream)
    h.context.load_verify_locations.assert_called_once_with(cafile=str(h.ca_file))
    h.context.load_default_certs.assert_not_called()
    h.context.load_cert_chain.assert_not_called()
    h.context.set_alpn_protocols.assert_called_once_with(["http/1.1"])
    assert h.context.verify_mode == ssl.CERT_REQUIRED
    assert h.context.check_hostname is True
    assert h.context.hostname_checks_common_name is False
    assert h.context.minimum_version == ssl.TLSVersion.TLSv1_2
    assert h.context.post_handshake_auth is False
    assert h.context.wrap_bio.call_args.kwargs["server_hostname"] == TARGET.hostname
    h.tls.do_handshake.assert_called_once()
    h.raw.connect_ex.assert_not_called()
    h.raw.close.assert_not_called()
    stream.close()
    h.raw.close.assert_called_once()
    h.tls.unwrap.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("target", "lifetime", "code"),
    [
        (NetworkTarget("010.44.0.1", 8443, "peer.test", "origin"), 5, FetchCode.DESTINATION),
        (NetworkTarget("10.44.0.1", 8443, "peer.test", "resolver"), 5, FetchCode.CONFIG),
        (TARGET, -1, FetchCode.TIMEOUT),
    ],
)
async def test_broker_tls_invalid_target_or_deadline_closes_before_tls(
    tls_harness: TLSHarness, target: NetworkTarget, lifetime: float, code: FetchCode
) -> None:
    h = tls_harness
    with pytest.raises(FetchError) as caught:
        await carrier(h.raw, target=target, lifetime=lifetime).wrap_tls(ca_file=h.ca_file)
    assert caught.value.code is code
    h.context.wrap_bio.assert_not_called()
    h.raw.send.assert_not_called()
    h.raw.close.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("stage", "failure", "expected", "code"),
    [
        ("context", OSError("private trust failure"), FetchError, FetchCode.CONFIG),
        ("handshake", ssl.SSLCertVerificationError("private identity failure"), FetchError, FetchCode.TLS),
        ("handshake", RuntimeError("unexpected failure"), RuntimeError, None),
        ("handshake", asyncio.CancelledError(), asyncio.CancelledError, None),
    ],
)
async def test_broker_tls_failure_closes_carrier_without_application_or_reconnect(
    tls_harness: TLSHarness,
    stage: str,
    failure: BaseException,
    expected: type[BaseException],
    code: FetchCode | None,
) -> None:
    h = tls_harness
    if stage == "context":
        h.context.load_verify_locations.side_effect = failure
    else:
        h.tls.do_handshake.side_effect = failure
    with pytest.raises(expected) as caught:
        await carrier(h.raw).wrap_tls(ca_file=h.ca_file)
    if code is not None:
        assert isinstance(caught.value, FetchError)
        assert caught.value.code is code
        assert "private" not in str(caught.value)
    else:
        assert caught.value is failure
    h.raw.send.assert_not_called()
    h.raw.connect_ex.assert_not_called()
    h.raw.close.assert_called_once()
    h.tls.unwrap.assert_not_called()
