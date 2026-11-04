"""Exercise explicit public-root trust against a synthetic local TLS authority."""

from __future__ import annotations

import asyncio
import ipaddress
import ssl
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx2
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from lychd.lib import http


def _tls_material(tmp_path: Path) -> tuple[ssl.SSLContext, str, Path]:
    now = datetime.now(UTC)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "LychD synthetic HTTP client CA")])
    ca = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    key = ec.generate_private_key(ec.SECP256R1())
    certificate = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
        .issuer_name(ca_name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    cert_path, key_path, ca_path = (tmp_path / name for name in ("server.pem", "server.key", "ca.pem"))
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    )
    key_path.chmod(0o600)
    ca_pem = ca.public_bytes(serialization.Encoding.PEM).decode()
    ca_path.write_text(ca_pem, encoding="ascii")
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(cert_path, key_path)
    return server_context, ca_pem, ca_path


@pytest.mark.asyncio
async def test_json_client_refuses_ambient_ca_and_accepts_explicit_verified_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    server_context, ca_pem, ca_path = _tls_material(tmp_path)
    requests: list[bytes] = []
    finished = asyncio.Event()

    async def respond(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            async with asyncio.timeout(2):
                requests.append(await reader.readuntil(b"\r\n\r\n"))
                body = b'{"status":"ok"}'
                writer.write(
                    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
                    + str(len(body)).encode()
                    + b"\r\nConnection: close\r\n\r\n"
                    + body
                )
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()
            finished.set()

    server = await asyncio.start_server(respond, "127.0.0.1", 0, ssl=server_context, ssl_handshake_timeout=2)
    async with server, asyncio.timeout(5):
        endpoint = f"https://127.0.0.1:{server.sockets[0].getsockname()[1]}/health"
        monkeypatch.setenv("SSL_CERT_FILE", str(ca_path))
        monkeypatch.setenv("SSL_CERT_DIR", str(tmp_path))
        key_log = tmp_path / "ambient-tls-keys"
        monkeypatch.setenv("SSLKEYLOGFILE", str(key_log))
        with pytest.raises(http.HttpJsonError) as refused:
            await http.request_json("GET", endpoint, timeout=2)
        assert refused.value.transport is True
        assert isinstance(refused.value.__cause__, httpx2.ConnectError)
        assert requests == []
        assert not key_log.exists()

        monkeypatch.delenv("SSLKEYLOGFILE")
        context = ssl.create_default_context()
        context.load_verify_locations(cadata=ca_pem)
        original_client = httpx2.AsyncClient

        def verified_client(**kwargs: Any) -> httpx2.AsyncClient:
            assert kwargs["trust_env"] is False
            assert kwargs["follow_redirects"] is False
            kwargs["verify"] = context
            return original_client(**kwargs)

        monkeypatch.setattr(httpx2, "AsyncClient", verified_client)
        assert await http.request_json("GET", endpoint, timeout=2) == {"status": "ok"}
        await finished.wait()
        assert len(requests) == 1
        assert requests[0].startswith(b"GET /health HTTP/1.1\r\n")
