"""Create the two installation-scoped TLS identities used for desktop inference."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from lychd.system.desktop.private import private_directory, publish_file
from lychd.system.desktop.reactor_link import SERVER_NAME


def create_identities(root: Path) -> None:
    """Issue a host and a Vessel leaf. The signing key exists only during preparation."""
    now = datetime.now(UTC)
    authority = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "LychD desktop inference")])
    issuer = ec.generate_private_key(ec.SECP256R1())

    def certificate(subject: x509.Name, key: ec.EllipticCurvePrivateKey) -> x509.CertificateBuilder:
        return (
            x509.CertificateBuilder()
            .issuer_name(authority)
            .subject_name(subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=365))
        )

    def key_usage(*, ca: bool) -> x509.KeyUsage:
        return x509.KeyUsage(
            digital_signature=not ca,
            content_commitment=False,
            key_encipherment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=ca,
            crl_sign=ca,
            encipher_only=False,
            decipher_only=False,
        )

    ca = (
        certificate(authority, issuer)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(key_usage(ca=True), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(issuer.public_key()), critical=False)
        .sign(issuer, hashes.SHA256())
    )
    for role, name, usage in (
        ("host", SERVER_NAME, ExtendedKeyUsageOID.SERVER_AUTH),
        ("vessel", "vessel.lychd.local", ExtendedKeyUsageOID.CLIENT_AUTH),
    ):
        path = root / role
        private_directory(path)
        key = ec.generate_private_key(ec.SECP256R1())
        leaf = (
            certificate(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)]), key)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(key_usage(ca=False), critical=True)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer.public_key()), critical=False)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(name)]), critical=False)
            .add_extension(x509.ExtendedKeyUsage([usage]), critical=False)
            .sign(issuer, hashes.SHA256())
        )
        publish_file(path / "ca.pem", ca.public_bytes(serialization.Encoding.PEM))
        publish_file(path / "identity.pem", leaf.public_bytes(serialization.Encoding.PEM))
        publish_file(
            path / "identity.key",
            key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
            ),
        )
