"""Secret-free, immutable application requests; these values confer no provider authority."""

from __future__ import annotations

import json
import re
import unicodedata
from hashlib import sha256
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

type Provider = Literal[
    "gmail", "fastmail", "discord", "telegram", "whatsapp", "github", "radicle", "facebook", "linkedin", "x"
]
type Operation = Literal["read", "send"]
type Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

_MAX_EMAIL_ADDRESS = 254
_MAX_EMAIL_LOCAL = 64
_MAX_DOMAIN_LABEL = 63
_MAX_RECIPIENTS = 50
_MAX_TTL = 3600
_MAX_HEADER_VALUE = 256
_MAX_QUERY_KEY = 64
_MAX_QUERY_VALUE = 4096


def safe_text(value: str, *, multiline: bool = False) -> str:
    """Refuse hidden controls without changing the exact proposed text."""
    if any(unicodedata.category(char).startswith("C") and not (multiline and char in "\n\t") for char in value):
        msg = "Control characters are not admitted."
        raise ValueError(msg)
    return value


def safe_identifier(value: str) -> str:
    safe_text(value)
    if not value or value != value.strip():
        msg = "An exact nonempty identifier is required."
        raise ValueError(msg)
    return value


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def record_digest(value: BaseModel) -> str:
    return sha256(canonical_json(value.model_dump(mode="json")).encode("utf-8")).hexdigest()


class Record(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, strict=True, hide_input_in_errors=True, revalidate_instances="always"
    )


class Connection(Record):
    """Operator-selected provider binding, not verified identity or a credential grant."""

    connection_id: str = Field(min_length=1, max_length=128)
    partition_id: str = Field(min_length=1, max_length=128)
    provider: Provider
    account_id: str = Field(min_length=1, max_length=512)
    actor_id: str = Field(min_length=1, max_length=512)
    profile_revision: str = Field(default="1", min_length=1, max_length=32)

    @field_validator("connection_id", "partition_id", "account_id", "actor_id", "profile_revision")
    @classmethod
    def exact_identifiers(cls, value: str) -> str:
        return safe_identifier(value)


class TargetRecord(Record):
    connection_id: str = Field(min_length=1, max_length=128)

    @field_validator("connection_id")
    @classmethod
    def exact_connection(cls, value: str) -> str:
        return safe_identifier(value)


def mailbox_address(value: str) -> str:
    """Accept plain ASCII addr-specs without display-name header syntax."""
    safe_identifier(value)
    if (
        len(value) > _MAX_EMAIL_ADDRESS
        or re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+", value) is None
    ):
        msg = "A plain ASCII mailbox address is required."
        raise ValueError(msg)
    local, domain = value.rsplit("@", 1)
    if (
        len(local) > _MAX_EMAIL_LOCAL
        or local.startswith(".")
        or local.endswith(".")
        or ".." in local
        or any(
            not label or len(label) > _MAX_DOMAIN_LABEL or label.startswith("-") or label.endswith("-")
            for label in domain.split(".")
        )
    ):
        msg = "The mailbox address has an invalid local part or domain."
        raise ValueError(msg)
    return value


class EmailTarget(TargetRecord):
    kind: Literal["email"] = "email"
    mailbox_id: str = Field(min_length=1, max_length=512)
    sender: str = Field(min_length=1, max_length=254)
    to: tuple[str, ...] = Field(default=(), max_length=50)
    cc: tuple[str, ...] = Field(default=(), max_length=50)
    bcc: tuple[str, ...] = Field(default=(), max_length=50, repr=False)
    thread_id: str | None = Field(default=None, min_length=1, max_length=512)
    identity_id: str | None = Field(default=None, min_length=1, max_length=512)
    draft_mailbox_id: str | None = Field(default=None, min_length=1, max_length=512)

    @field_validator("mailbox_id", "thread_id", "identity_id", "draft_mailbox_id")
    @classmethod
    def exact_identifiers(cls, value: str | None) -> str | None:
        return None if value is None else safe_identifier(value)

    @field_validator("sender")
    @classmethod
    def exact_sender(cls, value: str) -> str:
        return mailbox_address(value)

    @field_validator("to", "cc", "bcc")
    @classmethod
    def exact_addresses(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            mailbox_address(value)
        return values

    @model_validator(mode="after")
    def unique_recipients(self) -> Self:
        recipients = self.to + self.cc + self.bcc
        if len(recipients) != len(set(recipients)) or len(recipients) > _MAX_RECIPIENTS:
            msg = "Email requires at most fifty distinct envelope recipients."
            raise ValueError(msg)
        return self


class ChatTarget(TargetRecord):
    kind: Literal["chat"] = "chat"
    conversation_id: str = Field(min_length=1, max_length=512)
    reply_to_id: str | None = Field(default=None, min_length=1, max_length=512)

    @field_validator("conversation_id", "reply_to_id")
    @classmethod
    def exact_identifiers(cls, value: str | None) -> str | None:
        return None if value is None else safe_identifier(value)


class ForgeTarget(TargetRecord):
    kind: Literal["forge"] = "forge"
    repository: str = Field(min_length=1, max_length=512)
    issue_number: int = Field(ge=1, le=2**53 - 1)

    @field_validator("repository")
    @classmethod
    def exact_repository(cls, value: str) -> str:
        safe_identifier(value)
        if any(part in {"", ".", ".."} for part in value.split("/")) or any(char in value for char in "?%#\\"):
            msg = "A repository identifier cannot inject a route."
            raise ValueError(msg)
        return value


class SocialTarget(TargetRecord):
    kind: Literal["social"] = "social"
    account_id: str = Field(min_length=1, max_length=512)
    actor_kind: Literal["page", "member", "organization", "user"] = "user"
    visibility: Literal["public", "unlisted", "private"] = "public"

    @field_validator("account_id")
    @classmethod
    def exact_account(cls, value: str) -> str:
        return safe_identifier(value)


type Target = Annotated[EmailTarget | ChatTarget | ForgeTarget | SocialTarget, Field(discriminator="kind")]


def validate_target(connection: Connection, target: Target) -> None:
    """Check local declared identity and provider family; authenticate neither."""
    families = {
        "gmail": "email",
        "fastmail": "email",
        "discord": "chat",
        "telegram": "chat",
        "whatsapp": "chat",
        "github": "forge",
        "radicle": "forge",
        "facebook": "social",
        "linkedin": "social",
        "x": "social",
    }
    if target.connection_id != connection.connection_id or target.kind != families[connection.provider]:
        msg = "Target and connection do not identify the same provider family."
        raise ValueError(msg)
    if isinstance(target, EmailTarget):
        expected_mailbox = "me" if connection.provider == "gmail" else connection.account_id
        if target.mailbox_id != expected_mailbox or target.sender != connection.actor_id:
            msg = "Email mailbox and sender differ from the selected connection."
            raise ValueError(msg)
    if isinstance(target, SocialTarget) and target.account_id != connection.actor_id:
        msg = "Social target differs from the selected publishing actor."
        raise ValueError(msg)
    if isinstance(target, SocialTarget):
        if connection.provider == "facebook" and target.actor_kind != "page":
            msg = "Facebook preparation supports a Page actor only."
            raise ValueError(msg)
        if connection.provider == "x" and target.actor_kind != "user":
            msg = "X preparation requires a user actor."
            raise ValueError(msg)
        if connection.provider == "linkedin":
            expected_prefix = {"member": "urn:li:person:", "organization": "urn:li:organization:"}.get(
                target.actor_kind
            )
            if expected_prefix is None or not target.account_id.startswith(expected_prefix):
                msg = "LinkedIn preparation requires an exact member or organization actor URN."
                raise ValueError(msg)


class RequestRecord(Record):
    request_id: str = Field(min_length=1, max_length=128)
    target: Target = Field(repr=False)

    @field_validator("request_id")
    @classmethod
    def exact_request(cls, value: str) -> str:
        return safe_identifier(value)


class ReadRequest(RequestRecord):
    kind: Literal["read"] = "read"
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = Field(default=None, min_length=1, max_length=2048, repr=False)

    @field_validator("cursor")
    @classmethod
    def exact_cursor(cls, value: str | None) -> str | None:
        return None if value is None else safe_identifier(value)


class SendRequest(RequestRecord):
    kind: Literal["send"] = "send"
    text: str = Field(min_length=1, max_length=100_000, repr=False)
    subject: str | None = Field(default=None, min_length=1, max_length=998, repr=False)
    reply_to_id: str | None = Field(default=None, min_length=1, max_length=998)

    @field_validator("text")
    @classmethod
    def exact_text(cls, value: str) -> str:
        safe_text(value, multiline=True)
        if not value.strip():
            msg = "A communication requires nonempty text."
            raise ValueError(msg)
        return value

    @field_validator("subject", "reply_to_id")
    @classmethod
    def exact_headers(cls, value: str | None) -> str | None:
        return None if value is None else safe_identifier(value)

    @model_validator(mode="after")
    def channel_fields(self) -> Self:
        if isinstance(self.target, EmailTarget):
            if not self.target.to + self.target.cc + self.target.bcc or self.subject is None:
                msg = "Email send preparation requires recipients and an explicit subject."
                raise ValueError(msg)
        elif self.subject is not None:
            msg = "A subject belongs only to an email request."
            raise ValueError(msg)
        if (
            isinstance(self.target, ChatTarget)
            and self.reply_to_id is not None
            and self.target.reply_to_id != self.reply_to_id
        ):
            msg = "Chat reply references must agree with the admitted target."
            raise ValueError(msg)
        return self


type CorrespondenceRequest = Annotated[ReadRequest | SendRequest, Field(discriminator="kind")]


class ConnectedPolicy(Record):
    """Finite local preparation selection, not standing delivery permission."""

    policy_id: str = Field(min_length=1, max_length=128)
    revision: str = Field(default="1", min_length=1, max_length=32)
    connections: tuple[Connection, ...] = Field(min_length=1, max_length=32)
    allowed_targets: tuple[Target, ...] = Field(min_length=1, max_length=128, repr=False)
    operations: tuple[Operation, ...] = Field(default=("read",), min_length=1, max_length=2)
    max_text_chars: int = Field(default=10_000, ge=1, le=100_000)
    max_read_limit: int = Field(default=100, ge=1, le=100)
    ttl_seconds: int = Field(default=300, ge=1, le=3600)
    max_batch_size: int = Field(default=16, ge=1, le=32)

    @field_validator("policy_id", "revision")
    @classmethod
    def exact_identifiers(cls, value: str) -> str:
        return safe_identifier(value)

    @model_validator(mode="after")
    def exact_selection(self) -> Self:
        connections = {item.connection_id: item for item in self.connections}
        if len(connections) != len(self.connections) or len({item.partition_id for item in self.connections}) != 1:
            msg = "Preparation policy requires distinct connections in one partition."
            raise ValueError(msg)
        if len(set(self.operations)) != len(self.operations):
            msg = "Preparation operations must be distinct."
            raise ValueError(msg)
        if len({record_digest(target) for target in self.allowed_targets}) != len(self.allowed_targets):
            msg = "Preparation targets must be distinct."
            raise ValueError(msg)
        for target in self.allowed_targets:
            connection = connections.get(target.connection_id)
            if connection is None:
                msg = "A preparation target has no configured connection."
                raise ValueError(msg)
            validate_target(connection, target)
        return self

    @property
    def digest(self) -> str:
        return record_digest(self)


class PreparedOperation(Record):
    """Pinned application preparation, unsuitable as an authorization or delivery receipt."""

    request: CorrespondenceRequest = Field(repr=False)
    connection: Connection
    policy_digest: Digest
    prepared_at: AwareDatetime
    expires_at: AwareDatetime

    @model_validator(mode="after")
    def coherent_binding(self) -> Self:
        validate_target(self.connection, self.request.target)
        if self.expires_at <= self.prepared_at or (self.expires_at - self.prepared_at).total_seconds() > _MAX_TTL:
            msg = "Preparation requires a positive, bounded validity interval."
            raise ValueError(msg)
        if (
            self.connection.provider == "fastmail"
            and isinstance(self.request, SendRequest)
            and isinstance(self.request.target, EmailTarget)
            and (self.request.target.identity_id is None or self.request.target.draft_mailbox_id is None)
        ):
            msg = "Fastmail submission requires an explicit JMAP sending identity and draft mailbox."
            raise ValueError(msg)
        return self

    @property
    def digest(self) -> str:
        return record_digest(self)


class PreparedRequest(Record):
    """Exact application payload; a later owner must resolve route/auth and reauthorize."""

    preparation: PreparedOperation = Field(repr=False)
    method: Literal["GET", "POST"]
    route: str = Field(min_length=1, max_length=2048)
    query: tuple[tuple[str, str], ...] = Field(default=(), max_length=32, repr=False)
    headers: tuple[tuple[str, str], ...] = Field(default=(), max_length=8)
    body: str = Field(default="", max_length=1_000_000, repr=False)
    media_type: Literal["application/json", "message/rfc822", "application/x-www-form-urlencoded"] = "application/json"

    @field_validator("route")
    @classmethod
    def semantic_route(cls, value: str) -> str:
        safe_identifier(value)
        if (
            not value.isascii()
            or "://" in value
            or value.startswith("//")
            or any(char.isspace() or char in "?#%\\" for char in value)
            or any(part in {".", ".."} for part in value.split("/"))
        ):
            msg = "A preparation route must be a secret-free relative or symbolic route."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def bounded_wire_fields(self) -> Self:
        allowed_headers = {
            "accept",
            "content-type",
            "x-github-api-version",
            "linkedin-version",
            "x-restli-protocol-version",
        }
        seen_headers: set[str] = set()
        for key, value in self.headers:
            safe_identifier(key)
            safe_identifier(value)
            if key.lower() not in allowed_headers or key.lower() in seen_headers or len(value) > _MAX_HEADER_VALUE:
                msg = "Only distinct nonsecret protocol headers are admitted."
                raise ValueError(msg)
            seen_headers.add(key.lower())
        for key, value in self.query:
            safe_identifier(key)
            safe_text(value)
            if (
                len(key) > _MAX_QUERY_KEY
                or len(value) > _MAX_QUERY_VALUE
                or key.lower() in {"access_token", "token", "authorization", "api_key", "key", "password", "secret"}
            ):
                msg = "Preparation query must be bounded and secret-free."
                raise ValueError(msg)
        if len({key for key, _ in self.query}) != len(self.query):
            msg = "Ambiguous duplicate query fields are refused."
            raise ValueError(msg)
        # Encoding here also refuses surrogate code points before a digest or provider call.
        self.body.encode("utf-8")
        return self

    @property
    def wire_body(self) -> bytes:
        return self.body.encode("utf-8")

    @property
    def application_digest(self) -> str:
        return record_digest(self)


class PreparedBatch(Record):
    """All-preflight finite WUPHF plan; no native Graph broadcast or live effects."""

    operations: tuple[PreparedOperation, ...] = Field(min_length=1, max_length=32, repr=False)
    policy_digest: Digest
    prepared_at: AwareDatetime
    expires_at: AwareDatetime

    @model_validator(mode="after")
    def coherent_batch(self) -> Self:
        if any(
            (item.policy_digest, item.prepared_at, item.expires_at)
            != (self.policy_digest, self.prepared_at, self.expires_at)
            for item in self.operations
        ):
            msg = "Every batch operation must bind the same policy and preparation interval."
            raise ValueError(msg)
        if len({item.connection.partition_id for item in self.operations}) != 1:
            msg = "A batch cannot combine partitions."
            raise ValueError(msg)
        request_ids = [item.request.request_id for item in self.operations]
        targets = [(item.request.kind, record_digest(item.request.target)) for item in self.operations]
        if len(request_ids) != len(set(request_ids)) or len(targets) != len(set(targets)):
            msg = "A batch cannot duplicate a request or target operation."
            raise ValueError(msg)
        return self

    @property
    def digest(self) -> str:
        return record_digest(self)
