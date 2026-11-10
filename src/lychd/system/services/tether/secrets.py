"""Absent-only fixed key factories and immutable Podman-secret attestation."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from lychd.system.services.tether.custody import PreparationStore
from lychd.system.services.tether.models import PreparationReceipt, SecretIdentity, SelectedPreparation, TetherError

if TYPE_CHECKING:
    from uuid import UUID

    from lychd.domain.tether.models import CompiledTetherPlan, TetherSecretReference
    from lychd.system.operator.process import InputProcessRunner
    from lychd.system.services.tether.custody import TetherCustody


def _fingerprint(public_key: str) -> str:
    data = public_key.rsplit(" ", maxsplit=1)[-1]
    return "SHA256:" + base64.b64encode(hashlib.sha256(base64.b64decode(data, validate=True)).digest()).decode().rstrip(
        "="
    )


class TetherSecrets:
    """Create no replacement and adopt no secret merely because its name exists."""

    def __init__(
        self,
        plan: CompiledTetherPlan,
        custody: TetherCustody,
        runner: InputProcessRunner,
        *,
        podman_bin: str,
        wg_bin: str,
        ssh_keygen_bin: str,
    ) -> None:
        """Bind fixed native roles to trusted custody and process dependencies."""
        self.plan, self.custody, self.runner = plan, custody, runner
        self.podman, self.wg, self.ssh_keygen = podman_bin, wg_bin, ssh_keygen_bin

    def _run(self, argv: tuple[str, ...], *, input_text: str | None = None) -> str:
        if not argv[0]:
            msg = "The trusted server-key tool is unavailable; secret attestation remains incomplete"
            raise TetherError(msg)
        result = (
            self.runner.run(argv, timeout_s=30)
            if input_text is None
            else self.runner.run_with_input(argv, timeout_s=30, input_text=input_text)
        )
        if result.returncode:
            msg = "Tether server-secret command failed; private diagnostics suppressed"
            raise TetherError(msg)
        return result.stdout.strip()

    def _factory(self, purpose: str) -> tuple[str, str]:
        if purpose == "wireguard-server":
            private = self._run((self.wg, "genkey"))
            public = self._run((self.wg, "pubkey"), input_text=private + "\n")
            return private, public
        with tempfile.TemporaryDirectory(prefix=".ssh-factory-", dir=self.custody.directories["private"]) as scratch:
            key = Path(scratch) / "host"
            self._run((self.ssh_keygen, "-q", "-t", "ed25519", "-N", "", "-C", "", "-f", str(key)))
            private = key.read_text()
            public = " ".join(key.with_suffix(".pub").read_text().split()[:2])
            return private, public

    def _secret_data(self, payload: str, identity: SecretIdentity) -> str:
        raw: object = json.loads(payload)
        rows: list[object] = cast("list[object]", raw) if isinstance(raw, list) else []
        if len(rows) != 1:
            msg = "Prepared Tether secret has an invalid inspection shape"
            raise TetherError(msg)
        row = cast("dict[str, Any]", rows[0])
        if row["ID"] != identity.podman_id or row["Spec"]["Name"] != identity.name:
            msg = "Prepared Tether secret is absent, foreign or replaced"
            raise TetherError(msg)
        value = row["SecretData"]
        if not isinstance(value, str) or not value:
            msg = "Prepared Tether secret has no exact key material"
            raise TetherError(msg)
        return value

    def _inspect(self, identity: SecretIdentity) -> None:
        try:
            value = self._secret_data(
                self._run((self.podman, "secret", "inspect", "--showsecret", identity.podman_id)), identity
            )
            if identity.purpose == "wireguard-server":
                public = self._run((self.wg, "pubkey"), input_text=value + "\n")
            else:
                public = self._run((self.ssh_keygen, "-y", "-f", "/dev/stdin"), input_text=value)
            valid = public == identity.public_key and _fingerprint(public) == identity.fingerprint
        except (ValueError, KeyError, TypeError, IndexError):
            valid = False
        if not valid:
            msg = "Prepared Tether secret is absent, foreign or replaced"
            raise TetherError(msg)

    def _create(self, reference: TetherSecretReference, operation_id: UUID) -> SecretIdentity:
        name = f"secret-{reference.purpose}.json"
        existing = self.custody.read("private", name)
        if existing is not None:
            identity = SecretIdentity.model_validate_json(existing)
            if identity.name != reference.name or identity.purpose != reference.purpose:
                msg = "Prepared secret reference changed"
                raise TetherError(msg)
            self._inspect(identity)
            return identity
        pending = f"secret-{reference.purpose}.pending.json"
        if self.custody.read("private", pending) is not None:
            msg = "Uncertain server-secret creation; preserve and reconcile without adoption"
            raise TetherError(msg)
        probe = self.runner.run((self.podman, "secret", "exists", reference.name), timeout_s=5)
        if probe.returncode != 1:
            msg = "Server secret already exists or absence is unknown; refusing adoption"
            raise TetherError(msg)
        payload = json.dumps(
            {
                "installation_id": str(self.plan.envelope.installation_id),
                "operation_id": str(operation_id),
                "envelope_digest": self.plan.envelope_digest,
                "purpose": reference.purpose,
                "name": reference.name,
            }
        ).encode()
        self.custody.publish("private", pending, payload, immutable=True)
        private, public = self._factory(reference.purpose)
        podman_id = self._run((self.podman, "secret", "create", reference.name, "-"), input_text=private)
        identity = SecretIdentity(
            purpose=reference.purpose,
            name=reference.name,
            podman_id=podman_id,
            public_key=public,
            fingerprint=_fingerprint(public),
        )
        self._inspect(identity)
        self.custody.write("private", name, identity, immutable=True)
        return identity

    def preview_prepare(self) -> None:
        """Apply the same read-only secret/custody refusals without a factory."""
        present = os.path.lexists(self.custody.directories["private"])
        if present:
            self.custody.attest()
        elif os.path.lexists(self.custody.directories["public"]):
            msg = "Unreceipted Tether public custody exists"
            raise TetherError(msg)
        for reference in self.plan.secret_requirements:
            previous = self.custody.read("private", f"secret-{reference.purpose}.json") if present else None
            if previous is not None:
                identity = SecretIdentity.model_validate_json(previous)
                if (identity.purpose, identity.name) != (reference.purpose, reference.name):
                    msg = "Prepared secret reference changed"
                    raise TetherError(msg)
                self._inspect(identity)
                continue
            if present and self.custody.read("private", f"secret-{reference.purpose}.pending.json") is not None:
                msg = "Uncertain server-secret creation; preserve without adoption"
                raise TetherError(msg)
            probe = self.runner.run((self.podman, "secret", "exists", reference.name), timeout_s=5)
            if probe.returncode != 1:
                msg = "Server secret already exists or absence is unknown"
                raise TetherError(msg)

    def prepare(self, operation_id: UUID) -> PreparationReceipt:
        """Create both disjoint server secrets and retain immutable creation authority."""
        if self.custody.read("private", "preparation.json") is not None:
            return self.attest()
        self.custody.write("private", "plan.json", self.plan, immutable=True)
        identities = (
            self._create(self.plan.secret_requirements[0], operation_id),
            self._create(self.plan.secret_requirements[1], operation_id),
        )
        receipt = PreparationReceipt(
            installation_id=self.plan.envelope.installation_id,
            operation_id=operation_id,
            envelope_digest=self.plan.envelope_digest,
            secrets=identities,
        )
        self.custody.write("private", "preparation.json", receipt, immutable=True)
        return receipt

    def attest_selected(self) -> SelectedPreparation:
        """Attest existing selected identities even when this command proposes a new image."""
        selected = PreparationStore(self.custody).selected()
        gateway = TetherSecrets(
            selected.plan,
            self.custody,
            self.runner,
            podman_bin=self.podman,
            wg_bin=self.wg,
            ssh_keygen_bin=self.ssh_keygen,
        )
        if gateway.attest() != selected.preparation:
            msg = "Selected preparation changed during exact secret identity attestation"
            raise TetherError(msg)
        return selected

    def preparation_metadata(self) -> PreparationReceipt:
        """Read the selected public receipt without provisioning or key creation."""
        return PreparationStore(self.custody).selected().preparation

    def attest(self) -> PreparationReceipt:
        """Bind-time/startup check of both exact secret IDs and public fingerprints."""
        selected = PreparationStore(self.custody).selected()
        receipt = selected.preparation
        if selected.plan != self.plan:
            msg = "Preparation belongs to another installation or envelope"
            raise TetherError(msg)
        for reference, identity in zip(self.plan.secret_requirements, receipt.secrets, strict=True):
            if (reference.purpose, reference.name) != (identity.purpose, identity.name):
                msg = "Prepared secret roles disagree"
                raise TetherError(msg)
            created = self.custody.read("private", f"secret-{reference.purpose}.json")
            if created is None or SecretIdentity.model_validate_json(created) != identity:
                msg = "Preparation lacks exact immutable creation evidence"
                raise TetherError(msg)
            self._inspect(identity)
        return receipt
