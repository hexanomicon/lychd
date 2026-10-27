"""Reviewed local developer-server plans, separate from Reach and chat authority.

Planning is pure. Applying requires an exact digest, a fresh snapshot and the
operator effect journal. This module never deletes resources or grants membership.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from time import monotonic
from typing import Annotated, Any, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from lychd.interface.discord.rest import DiscordRest, DiscordRestError, EffectResult
from lychd.interface.discord.schemas import DiscordId

_VIEW = 1 << 10
_SEND = 1 << 11
_HISTORY = 1 << 16
_ADMIN = 1 << 3
_MANAGE_CHANNELS = 1 << 4
_MANAGE_ROLES = 1 << 28
_SAFE = _VIEW | _SEND | _HISTORY | (1 << 6) | (1 << 14) | (1 << 15) | (1 << 20) | (1 << 21) | (1 << 31)
_MAX_PERMISSIONS = (1 << 64) - 1
_MAX_SNAPSHOT_ITEMS = 1000
_MAX_DECIMAL_DIGITS = 20

type Key = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{0,47}$")]
type PermissionBits = Annotated[int, Field(ge=0, le=_MAX_PERMISSIONS)]
type ResourceKind = Literal["role", "category", "text", "voice"]


class AdminError(ValueError):
    """A fixed, content-free refusal safe for the operator CLI."""

    def __init__(self, code: str) -> None:
        """Retain only an operator-safe fixed code."""
        self.code = code
        super().__init__(code)


class _Value(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, hide_input_in_errors=True)

    @field_validator("schema_version", mode="before", check_fields=False)
    @classmethod
    def original_version(cls, value: object) -> object:
        if type(value) is not int:
            message = "Schema version must be an integer."
            raise ValueError(message)
        return value


def _canonical(value: _Value) -> bytes:
    return json.dumps(value.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        message = "An aware timestamp is required."
        raise ValueError(message)
    return value


class PermissionIntent(_Value):
    """Only ordinary collaboration permissions may be added to new resources."""

    target: Literal["everyone", "role", "member"]
    role_key: Key | None = None
    member_id: DiscordId | None = None
    allow: PermissionBits = 0
    deny: PermissionBits = 0

    @model_validator(mode="after")
    def check_target(self) -> Self:
        if self.allow & self.deny or (self.allow | self.deny) & ~_SAFE:
            message = "Unsupported permission intent."
            raise ValueError(message)
        if self.target == "role" and (self.role_key is None or self.member_id is not None):
            message = "Role target requires one role key."
            raise ValueError(message)
        if self.target == "member" and (self.member_id is None or self.role_key is not None):
            message = "Member target requires one member ID."
            raise ValueError(message)
        if self.target == "everyone" and (self.role_key is not None or self.member_id is not None):
            message = "Everyone target has no explicit identity."
            raise ValueError(message)
        return self


class RoleLayout(_Value):
    key: Key
    name: str = Field(min_length=1, max_length=100)
    permissions: PermissionBits = 0

    @field_validator("permissions")
    @classmethod
    def safe_permissions(cls, value: int) -> int:
        if value & ~_SAFE:
            message = "Administrative role grants are unsupported."
            raise ValueError(message)
        return value


class CategoryLayout(_Value):
    key: Key
    name: str = Field(min_length=1, max_length=100)
    existing_id: DiscordId | None = None
    overwrites: tuple[PermissionIntent, ...] = Field(default=(), max_length=16)


class ChannelLayout(_Value):
    key: Key
    name: str = Field(min_length=1, max_length=100)
    kind: Literal["text", "voice"] = "text"
    parent_key: Key
    topic: str | None = Field(default=None, max_length=1024)
    existing_id: DiscordId | None = None
    overwrites: tuple[PermissionIntent, ...] = Field(default=(), max_length=16)

    @model_validator(mode="after")
    def text_topic(self) -> Self:
        if self.kind == "voice" and self.topic is not None:
            message = "Voice channels have no text topic."
            raise ValueError(message)
        return self


class DeveloperLayout(_Value):
    """Explicit identities and additive developer-server intent; never chat consent."""

    schema_version: Literal[1] = 1
    application_id: DiscordId
    bot_user_id: DiscordId
    guild_id: DiscordId
    owner_id: DiscordId
    roles: tuple[RoleLayout, ...] = Field(default=(), max_length=8)
    categories: tuple[CategoryLayout, ...] = Field(default=(), max_length=8)
    channels: tuple[ChannelLayout, ...] = Field(default=(), max_length=16)

    @model_validator(mode="after")
    def references(self) -> Self:
        resources = (*self.roles, *self.categories, *self.channels)
        keys = [resource.key for resource in resources]
        if len(keys) != len(set(keys)):
            message = "Resource keys must be unique."
            raise ValueError(message)
        names = [resource.name for resource in (*self.categories, *self.channels)]
        if len(names) != len(set(names)) or len({role.name for role in self.roles}) != len(self.roles):
            message = "Intended resource names must be unique."
            raise ValueError(message)
        explicit = [resource.existing_id for resource in (*self.categories, *self.channels) if resource.existing_id]
        if len(explicit) != len(set(explicit)):
            message = "Existing IDs must be unique."
            raise ValueError(message)
        role_keys = {role.key for role in self.roles}
        category_keys = {category.key for category in self.categories}
        for channel in self.channels:
            if channel.parent_key not in category_keys:
                message = "Unknown parent key."
                raise ValueError(message)
        for resource in (*self.categories, *self.channels):
            targets: set[tuple[str, str | None]] = set()
            for overwrite in resource.overwrites:
                if overwrite.role_key is not None and overwrite.role_key not in role_keys:
                    message = "Unknown role key."
                    raise ValueError(message)
                target = (overwrite.target, overwrite.role_key or overwrite.member_id)
                if target in targets:
                    message = "Duplicate overwrite target."
                    raise ValueError(message)
                targets.add(target)
        return self


def developer_layout(
    *, guild_id: str, application_id: str, bot_user_id: str, owner_id: str, reach_channel_id: str
) -> DeveloperLayout:
    """Build a small developer server while retaining existing bot role authority."""
    private = (
        PermissionIntent(target="everyone", deny=_VIEW),
        PermissionIntent(target="role", role_key="core", allow=_VIEW | _SEND | _HISTORY),
        PermissionIntent(target="member", member_id=owner_id, allow=_VIEW | _SEND | _HISTORY),
        PermissionIntent(target="member", member_id=bot_user_id, allow=_VIEW | _SEND | _HISTORY),
    )
    readonly = (
        PermissionIntent(target="everyone", allow=_VIEW | _HISTORY, deny=_SEND),
        PermissionIntent(target="role", role_key="core", allow=_VIEW | _SEND | _HISTORY),
    )
    return DeveloperLayout(
        application_id=application_id,
        bot_user_id=bot_user_id,
        guild_id=guild_id,
        owner_id=owner_id,
        roles=tuple(
            RoleLayout(key=key, name=name)
            for key, name in (("core", "Core"), ("developer", "Developer"), ("contributor", "Contributor"))
        ),
        categories=(
            CategoryLayout(key="start", name="START"),
            CategoryLayout(key="development", name="DEVELOPMENT"),
            CategoryLayout(key="community", name="COMMUNITY"),
            CategoryLayout(key="operations", name="OPERATIONS", overwrites=private),
        ),
        channels=(
            ChannelLayout(
                key="start_here",
                name="start-here",
                parent_key="start",
                topic="Project links, contribution guide, and server orientation.",
                overwrites=readonly,
            ),
            ChannelLayout(
                key="announcements",
                name="announcements",
                parent_key="start",
                topic="Project milestones and release announcements.",
                overwrites=readonly,
            ),
            ChannelLayout(
                key="dev",
                name="dev",
                parent_key="development",
                topic="Engineering discussion and implementation coordination.",
            ),
            ChannelLayout(
                key="help", name="help", parent_key="development", topic="Development setup and contributor questions."
            ),
            ChannelLayout(
                key="reach",
                name="the-reach",
                parent_key="development",
                existing_id=reach_channel_id,
                topic="The Reach: explicitly authorized project documentation assistance.",
            ),
            ChannelLayout(key="general", name="general", parent_key="community"),
            ChannelLayout(
                key="ops",
                name="ops",
                parent_key="operations",
                overwrites=private,
                topic="Private project operations for the owner and Core role.",
            ),
            ChannelLayout(key="coworking", name="Coworking", kind="voice", parent_key="community"),
            ChannelLayout(key="meeting", name="Meeting", kind="voice", parent_key="community"),
        ),
    )


class OverwriteSnapshot(_Value):
    id: DiscordId
    type: Literal[0, 1]
    allow: PermissionBits
    deny: PermissionBits


class RoleSnapshot(_Value):
    id: DiscordId
    name: str
    permissions: PermissionBits
    position: int = Field(ge=0)
    managed: bool


class ChannelSnapshot(_Value):
    id: DiscordId
    type: int = Field(ge=0, le=255)
    name: str
    parent_id: DiscordId | None = None
    topic: str | None = None
    overwrites: tuple[OverwriteSnapshot, ...] = ()


class GuildSnapshot(_Value):
    application_id: DiscordId
    bot_user_id: DiscordId
    guild_id: DiscordId
    owner_id: DiscordId
    roles: tuple[RoleSnapshot, ...]
    channels: tuple[ChannelSnapshot, ...]
    bot_role_ids: tuple[DiscordId, ...]

    @model_validator(mode="after")
    def unique_resources(self) -> Self:
        if len({role.id for role in self.roles}) != len(self.roles) or len(
            {channel.id for channel in self.channels}
        ) != len(self.channels):
            message = "Duplicate snapshot identity."
            raise ValueError(message)
        if len(set(self.bot_role_ids)) != len(self.bot_role_ids):
            message = "Duplicate bot role identity."
            raise ValueError(message)
        return self

    @property
    def digest(self) -> str:
        return hashlib.sha256(_canonical(self)).hexdigest()


def _object(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        message = "invalid_snapshot"
        raise AdminError(message)
    return cast("dict[str, Any]", value)


def _items(value: object) -> list[Any]:
    if not isinstance(value, list):
        message = "invalid_snapshot"
        raise AdminError(message)
    items = cast("list[Any]", value)
    if len(items) > _MAX_SNAPSHOT_ITEMS:
        message = "invalid_snapshot"
        raise AdminError(message)
    return items


def _bits(value: object) -> int:
    if type(value) is not str or not value.isdecimal() or len(value) > _MAX_DECIMAL_DIGITS:
        message = "invalid_snapshot"
        raise AdminError(message)
    parsed = int(value)
    if not 0 <= parsed <= _MAX_PERMISSIONS:
        message = "invalid_snapshot"
        raise AdminError(message)
    return parsed


async def snapshot_guild(rest: DiscordRest) -> GuildSnapshot:
    """Read actual identities and the complete relevant permission/resource slice."""
    await rest.verify_identity()
    root = f"/guilds/{rest.guild_id}"
    guild = _object(await rest.get(root))
    raw_roles = _items(await rest.get(f"{root}/roles"))
    raw_channels = _items(await rest.get(f"{root}/channels"))
    member = _object(await rest.get(f"{root}/members/{rest.bot_user_id}"))
    try:
        if guild.get("id") != rest.guild_id or _object(member["user"]).get("id") != rest.bot_user_id:
            message = "snapshot_identity_mismatch"
            raise AdminError(message)
        roles: list[RoleSnapshot] = []
        for raw in raw_roles:
            row = _object(raw)
            roles.append(
                RoleSnapshot(
                    id=row["id"],
                    name=row["name"],
                    permissions=_bits(row["permissions"]),
                    position=row["position"],
                    managed=row.get("managed", False),
                )
            )
        channels: list[ChannelSnapshot] = []
        for raw in raw_channels:
            row = _object(raw)
            overwrites: list[OverwriteSnapshot] = []
            for raw_overwrite in _items(row.get("permission_overwrites", [])):
                overwrite = _object(raw_overwrite)
                overwrites.append(
                    OverwriteSnapshot(
                        id=overwrite["id"],
                        type=overwrite["type"],
                        allow=_bits(overwrite["allow"]),
                        deny=_bits(overwrite["deny"]),
                    )
                )
            channels.append(
                ChannelSnapshot(
                    id=row["id"],
                    name=row["name"],
                    type=row["type"],
                    parent_id=row.get("parent_id"),
                    topic=row.get("topic"),
                    overwrites=tuple(sorted(overwrites, key=lambda item: (item.type, item.id))),
                )
            )
        snapshot = GuildSnapshot(
            application_id=rest.application_id,
            bot_user_id=rest.bot_user_id,
            guild_id=rest.guild_id,
            owner_id=guild["owner_id"],
            roles=tuple(sorted(roles, key=lambda item: item.id)),
            channels=tuple(sorted(channels, key=lambda item: item.id)),
            bot_role_ids=tuple(sorted(_items(member["roles"]))),
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, AdminError):
            raise
        message = "invalid_snapshot"
        raise AdminError(message) from None
    rest.bind_channels(channel.id for channel in snapshot.channels)
    return snapshot


class ResourceBinding(_Value):
    key: Key
    kind: ResourceKind
    remote_id: DiscordId


class AdminOperation(_Value):
    key: Key
    kind: ResourceKind
    action: Literal["create", "patch"]
    target_id: DiscordId | None = None

    @model_validator(mode="after")
    def target(self) -> Self:
        if (self.action == "patch") != (self.target_id is not None) or (self.kind == "role" and self.action == "patch"):
            message = "Unsupported operation target."
            raise ValueError(message)
        return self


class ServerPlan(_Value):
    schema_version: Literal[1] = 1
    created_at: datetime
    expires_at: datetime
    layout: DeveloperLayout
    snapshot: GuildSnapshot
    existing: tuple[ResourceBinding, ...]
    operations: tuple[AdminOperation, ...] = Field(max_length=32)

    @field_validator("created_at", "expires_at")
    @classmethod
    def aware_time(cls, value: datetime) -> datetime:
        return _aware(value)

    @model_validator(mode="after")
    def expiry(self) -> Self:
        if not timedelta(0) < self.expires_at - self.created_at <= timedelta(minutes=15):
            message = "Plan expiry must be within fifteen minutes."
            raise ValueError(message)
        return self

    @property
    def digest(self) -> str:
        return hashlib.sha256(_canonical(self)).hexdigest()


def _identity(layout: DeveloperLayout, snapshot: GuildSnapshot) -> None:
    if (layout.application_id, layout.bot_user_id, layout.guild_id, layout.owner_id) != (
        snapshot.application_id,
        snapshot.bot_user_id,
        snapshot.guild_id,
        snapshot.owner_id,
    ):
        message = "layout_identity_mismatch"
        raise AdminError(message)
    own_roles = [role for role in snapshot.roles if role.id == snapshot.guild_id or role.id in snapshot.bot_role_ids]
    permissions = 0
    for role in own_roles:
        permissions |= role.permissions
    if not permissions & _ADMIN and permissions & (_MANAGE_CHANNELS | _MANAGE_ROLES) != (
        _MANAGE_CHANNELS | _MANAGE_ROLES
    ):
        message = "bot_permissions_insufficient"
        raise AdminError(message)


def _resolve_overwrites(
    intents: tuple[PermissionIntent, ...], layout: DeveloperLayout, bindings: dict[str, str]
) -> tuple[OverwriteSnapshot, ...]:
    results: list[OverwriteSnapshot] = []
    for intent in intents:
        if intent.target == "everyone":
            target, target_type = layout.guild_id, 0
        elif intent.target == "member":
            target, target_type = intent.member_id, 1
        else:
            target, target_type = bindings.get(intent.role_key or ""), 0
        if target is None:
            message = "unresolved_resource"
            raise AdminError(message)
        results.append(OverwriteSnapshot(id=target, type=target_type, allow=intent.allow, deny=intent.deny))
    return tuple(sorted(results, key=lambda item: (item.type, item.id)))


def _merged_overwrites(
    existing: tuple[OverwriteSnapshot, ...], desired: tuple[OverwriteSnapshot, ...]
) -> tuple[OverwriteSnapshot, ...]:
    merged = {(item.type, item.id): item for item in existing}
    for item in desired:
        old = merged.get((item.type, item.id))
        mask = item.allow | item.deny
        merged[(item.type, item.id)] = (
            item
            if old is None
            else OverwriteSnapshot(
                id=item.id, type=item.type, allow=(old.allow & ~mask) | item.allow, deny=(old.deny & ~mask) | item.deny
            )
        )
    return tuple(sorted(merged.values(), key=lambda item: (item.type, item.id)))


def _channel_patch(
    spec: CategoryLayout | ChannelLayout, channel: ChannelSnapshot, layout: DeveloperLayout, bindings: dict[str, str]
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if channel.name != spec.name:
        payload["name"] = spec.name
    if isinstance(spec, ChannelLayout):
        parent = bindings.get(spec.parent_key)
        if parent is None:
            message = "unresolved_resource"
            raise AdminError(message)
        if channel.parent_id != parent:
            payload["parent_id"] = parent
        if spec.topic is not None and spec.topic != channel.topic:
            payload["topic"] = spec.topic
    if spec.overwrites:
        merged = _merged_overwrites(channel.overwrites, _resolve_overwrites(spec.overwrites, layout, bindings))
        if merged != channel.overwrites:
            payload["permission_overwrites"] = [_overwrite_payload(item) for item in merged]
    return payload


def _overwrite_payload(item: OverwriteSnapshot) -> dict[str, Any]:
    return {"id": item.id, "type": item.type, "allow": str(item.allow), "deny": str(item.deny)}


def _plan_role(role: RoleLayout, snapshot: GuildSnapshot) -> ResourceBinding | AdminOperation:
    matches = [item for item in snapshot.roles if item.name == role.name]
    if len(matches) > 1:
        message = "ambiguous_role"
        raise AdminError(message)
    if not matches:
        return AdminOperation(key=role.key, kind="role", action="create")
    match = matches[0]
    if match.managed or match.id == snapshot.guild_id or match.permissions != role.permissions:
        message = "conflicting_role"
        raise AdminError(message)
    return ResourceBinding(key=role.key, kind="role", remote_id=match.id)


def _match_channel(
    spec: CategoryLayout | ChannelLayout, snapshot: GuildSnapshot, *, reserved_ids: frozenset[str]
) -> ChannelSnapshot | None:
    kind = "category" if isinstance(spec, CategoryLayout) else spec.kind
    expected_type = {"category": 4, "text": 0, "voice": 2}[kind]
    matches = [item for item in snapshot.channels if item.name == spec.name]
    if spec.existing_id is not None:
        match = next((item for item in snapshot.channels if item.id == spec.existing_id), None)
        if match is None or match.type != expected_type:
            message = "explicit_channel_missing_or_wrong_type"
            raise AdminError(message)
        if any(item.id != match.id for item in matches):
            message = "ambiguous_channel"
            raise AdminError(message)
        return match
    matches = [item for item in matches if item.id not in reserved_ids]
    if len(matches) > 1:
        message = "ambiguous_channel"
        raise AdminError(message)
    if not matches:
        return None
    if matches[0].type != expected_type:
        message = "conflicting_channel"
        raise AdminError(message)
    return matches[0]


def _needs_patch(
    spec: CategoryLayout | ChannelLayout, match: ChannelSnapshot, layout: DeveloperLayout, bindings: dict[str, str]
) -> bool:
    try:
        different = bool(_channel_patch(spec, match, layout, bindings))
        if spec.existing_id is None:
            different = different or match.overwrites != _resolve_overwrites(spec.overwrites, layout, bindings)
    except AdminError as exc:
        if spec.existing_id is None:
            message = "conflicting_channel"
            raise AdminError(message) from None
        if exc.code != "unresolved_resource":
            raise
        return True
    if different and spec.existing_id is None:
        message = "conflicting_channel"
        raise AdminError(message)
    return different


def _ordered_operations(
    layout: DeveloperLayout, snapshot: GuildSnapshot, operations: list[AdminOperation]
) -> tuple[AdminOperation, ...]:
    specs = {item.key: item for item in (*layout.roles, *layout.categories, *layout.channels)}
    reserved = {item.existing_id: item.key for item in (*layout.categories, *layout.channels) if item.existing_id}
    operation_keys = {item.key for item in operations}
    role_keys = {item.key for item in operations if item.kind == "role"}
    dependencies: dict[str, set[str]] = {}
    for operation in operations:
        required: set[str] = set() if operation.kind == "role" else set(role_keys)
        spec = specs[operation.key]
        if isinstance(spec, ChannelLayout) and spec.parent_key in operation_keys:
            required.add(spec.parent_key)
        if operation.kind != "role" and operation.action == "create":
            blockers = {
                reserved[item.id] for item in snapshot.channels if item.id in reserved and item.name == spec.name
            }
            if not blockers <= operation_keys:
                message = "reserved_channel_name_not_released"
                raise AdminError(message)
            required.update(blockers)
        dependencies[operation.key] = required
    return _sort_operations(operations, dependencies)


def _sort_operations(operations: list[AdminOperation], dependencies: dict[str, set[str]]) -> tuple[AdminOperation, ...]:
    pending = list(operations)
    completed: set[str] = set()
    ordered: list[AdminOperation] = []
    while pending:
        ready = [item for item in pending if dependencies[item.key] <= completed]
        if not ready:
            message = "layout_dependency_cycle"
            raise AdminError(message)
        selected = ready[0]
        pending.remove(selected)
        ordered.append(selected)
        completed.add(selected.key)
    return tuple(ordered)


def plan_layout(layout: DeveloperLayout, snapshot: GuildSnapshot, *, now: datetime) -> ServerPlan:
    """Compute additive operations; names establish exact, report-only matches."""
    _aware(now)
    _identity(layout, snapshot)
    existing: list[ResourceBinding] = []
    operations: list[AdminOperation] = []
    bindings: dict[str, str] = {}
    reserved_ids = frozenset(item.existing_id for item in (*layout.categories, *layout.channels) if item.existing_id)
    for role in layout.roles:
        planned = _plan_role(role, snapshot)
        if isinstance(planned, ResourceBinding):
            existing.append(planned)
            bindings[planned.key] = planned.remote_id
        else:
            operations.append(planned)
    for spec in (*layout.categories, *layout.channels):
        kind: ResourceKind = "category" if isinstance(spec, CategoryLayout) else spec.kind
        match = _match_channel(spec, snapshot, reserved_ids=reserved_ids)
        if match is None:
            operations.append(AdminOperation(key=spec.key, kind=kind, action="create"))
            continue
        existing.append(ResourceBinding(key=spec.key, kind=kind, remote_id=match.id))
        bindings[spec.key] = match.id
        if _needs_patch(spec, match, layout, bindings):
            operations.append(AdminOperation(key=spec.key, kind=kind, action="patch", target_id=match.id))
    return ServerPlan(
        created_at=now,
        expires_at=now + timedelta(minutes=15),
        layout=layout,
        snapshot=snapshot,
        existing=tuple(existing),
        operations=_ordered_operations(layout, snapshot, operations),
    )


class AppliedOperation(_Value):
    key: Key
    status: Literal["succeeded", "rejected", "unknown"]
    remote_id: DiscordId | None = None
    code: str | None = None


class AdminApplyResult(_Value):
    status: Literal["succeeded", "rejected", "unknown"]
    code: str | None = None
    operations: tuple[AppliedOperation, ...] = ()
    resources: tuple[ResourceBinding, ...] = ()


def _operation_body(operation: AdminOperation, plan: ServerPlan, bindings: dict[str, str]) -> dict[str, Any]:
    layout = plan.layout
    if operation.kind == "role":
        spec = next(item for item in layout.roles if item.key == operation.key)
        return {"name": spec.name, "permissions": str(spec.permissions), "hoist": False, "mentionable": False}
    spec = next(item for item in (*layout.categories, *layout.channels) if item.key == operation.key)
    if operation.action == "patch":
        channel = next(item for item in plan.snapshot.channels if item.id == operation.target_id)
        return _channel_patch(spec, channel, layout, bindings)
    payload: dict[str, Any] = {
        "name": spec.name,
        "type": {"category": 4, "text": 0, "voice": 2}[operation.kind],
        "permission_overwrites": [
            _overwrite_payload(item) for item in _resolve_overwrites(spec.overwrites, layout, bindings)
        ],
    }
    if isinstance(spec, ChannelLayout):
        payload["parent_id"] = bindings[spec.parent_key]
        if spec.topic is not None:
            payload["topic"] = spec.topic
    return payload


def _created_matches(
    operation: AdminOperation, body: dict[str, Any], result: EffectResult, snapshot: GuildSnapshot
) -> bool:
    if result.remote_id is None:
        return False
    if operation.kind == "role":
        candidates = [item for item in snapshot.roles if item.name == body["name"]]
        return (
            len(candidates) == 1
            and candidates[0].id == result.remote_id
            and not candidates[0].managed
            and str(candidates[0].permissions) == body["permissions"]
        )
    candidates = [item for item in snapshot.channels if item.name == body["name"]]
    if len(candidates) != 1 or candidates[0].id != result.remote_id:
        return False
    channel = candidates[0]
    expected = tuple(
        sorted(
            (
                OverwriteSnapshot(id=item["id"], type=item["type"], allow=int(item["allow"]), deny=int(item["deny"]))
                for item in body["permission_overwrites"]
            ),
            key=lambda item: (item.type, item.id),
        )
    )
    return (
        channel.type == body["type"]
        and channel.parent_id == body.get("parent_id")
        and ("topic" not in body or channel.topic == body["topic"])
        and channel.overwrites == expected
    )


def _only_created(
    before: GuildSnapshot, after: GuildSnapshot, operation: AdminOperation, remote_id: str | None
) -> bool:
    """Refuse concurrent changes, allowing only the intended resource addition."""
    if remote_id is None or (
        before.application_id,
        before.bot_user_id,
        before.guild_id,
        before.owner_id,
        before.bot_role_ids,
    ) != (after.application_id, after.bot_user_id, after.guild_id, after.owner_id, after.bot_role_ids):
        return False
    if operation.kind != "role":
        return (
            before.roles == after.roles
            and before.channels == tuple(item for item in after.channels if item.id != remote_id)
            and len(after.channels) == len(before.channels) + 1
        )
    if before.channels != after.channels or len(after.roles) != len(before.roles) + 1:
        return False
    old = {item.id: item for item in before.roles}
    remaining = {item.id: item for item in after.roles if item.id != remote_id}
    if old.keys() != remaining.keys():
        return False
    # Discord inserts the new role into its order. Identity, permissions and the
    # relative order of pre-existing roles must remain unchanged.
    for identity, role in old.items():
        updated = remaining[identity]
        if role.model_dump(exclude={"position"}) != updated.model_dump(exclude={"position"}):
            return False
    previous_order = [item.id for item in sorted(old.values(), key=lambda item: (item.position, item.id))]
    current_order = [item.id for item in sorted(remaining.values(), key=lambda item: (item.position, item.id))]
    return previous_order == current_order


def _only_patched(before: GuildSnapshot, after: GuildSnapshot, target_id: str | None, body: dict[str, Any]) -> bool:
    if target_id is None:
        return False
    target = next((item for item in before.channels if item.id == target_id), None)
    if target is None:
        return False
    changes = dict(body)
    if "permission_overwrites" in changes:
        changes["overwrites"] = tuple(
            OverwriteSnapshot.model_validate({**item, "allow": int(item["allow"]), "deny": int(item["deny"])})
            for item in changes.pop("permission_overwrites")
        )
    expected = before.model_copy(
        update={
            "channels": tuple(
                item.model_copy(update=changes) if item.id == target_id else item for item in before.channels
            )
        }
    )
    return expected == after


def _operation_scope(operation: AdminOperation, plan: ServerPlan) -> str:
    if operation.target_id is not None:
        selector = operation.target_id
    else:
        specs = plan.layout.roles if operation.kind == "role" else (*plan.layout.categories, *plan.layout.channels)
        selector = next(item.name for item in specs if item.key == operation.key)
    return f"admin:{plan.layout.application_id}:{plan.layout.guild_id}:{operation.kind}:{selector}"


def _check_plan(rest: DiscordRest, plan: ServerPlan, expected_digest: str, now: datetime) -> None:
    _aware(now)
    if expected_digest != plan.digest:
        message = "plan_digest_mismatch"
        raise AdminError(message)
    if not plan.created_at <= now < plan.expires_at:
        message = "plan_expired"
        raise AdminError(message)
    if (rest.application_id, rest.bot_user_id, rest.guild_id) != (
        plan.layout.application_id,
        plan.layout.bot_user_id,
        plan.layout.guild_id,
    ):
        message = "plan_identity_mismatch"
        raise AdminError(message)
    if plan_layout(plan.layout, plan.snapshot, now=plan.created_at) != plan:
        message = "plan_derivation_mismatch"
        raise AdminError(message)


async def _reconcile_operation(
    rest: DiscordRest,
    operation: AdminOperation,
    body: dict[str, Any],
    result: EffectResult,
    before: GuildSnapshot,
    effect_key: str,
) -> tuple[EffectResult, GuildSnapshot]:
    prefix = "create" if operation.action == "create" else "patch"
    code: str | None = None
    after = before
    try:
        after = await snapshot_guild(rest)
    except (DiscordRestError, AdminError, ValueError):
        code = f"{prefix}_reconciliation_failed"
    else:
        matches = (
            (
                _created_matches(operation, body, result, after)
                and _only_created(before, after, operation, result.remote_id)
            )
            if operation.action == "create"
            else _only_patched(before, after, operation.target_id, body)
        )
        if not matches:
            code = f"{prefix}_reconciliation_mismatch"
    if code is not None:
        rest.journal.mark_unknown(effect_key, code=code)
        return EffectResult(status="unknown", remote_id=result.remote_id, code=code), after
    return result, after


async def _apply_locked(rest: DiscordRest, plan: ServerPlan, *, deadline: float) -> AdminApplyResult:
    current = await snapshot_guild(rest)
    if current.digest != plan.snapshot.digest:
        return AdminApplyResult(status="rejected", code="plan_snapshot_stale")
    bindings = {item.key: item.remote_id for item in plan.existing}
    resources = list(plan.existing)
    results: list[AppliedOperation] = []
    for operation in plan.operations:
        body = _operation_body(operation, plan, bindings)
        path = (
            f"/guilds/{rest.guild_id}/{'roles' if operation.kind == 'role' else 'channels'}"
            if operation.action == "create"
            else f"/channels/{operation.target_id}"
        )
        effect_key = f"admin:{plan.digest}:{operation.key}"
        try:
            if monotonic() >= deadline:
                return AdminApplyResult(
                    status="rejected", code="plan_expired", operations=tuple(results), resources=tuple(resources)
                )
            result = await rest.write(
                "POST" if operation.action == "create" else "PATCH",
                path,
                body,
                effect_key=effect_key,
                scope=_operation_scope(operation, plan),
            )
            if result.status == "succeeded":
                result, current = await _reconcile_operation(rest, operation, body, result, current, effect_key)
        except DiscordRestError:
            result = EffectResult(status="unknown", code="admin_effect_unavailable")
        results.append(
            AppliedOperation(key=operation.key, status=result.status, remote_id=result.remote_id, code=result.code)
        )
        if result.status != "succeeded":
            return AdminApplyResult(
                status=result.status, code=result.code, operations=tuple(results), resources=tuple(resources)
            )
        if operation.action == "create" and result.remote_id is not None:
            bindings[operation.key] = result.remote_id
            resources.append(ResourceBinding(key=operation.key, kind=operation.kind, remote_id=result.remote_id))
    return AdminApplyResult(status="succeeded", resources=tuple(resources), operations=tuple(results))


async def apply_plan(rest: DiscordRest, plan: ServerPlan, *, expected_digest: str, now: datetime) -> AdminApplyResult:
    """Apply only an unchanged, reviewed local plan; stop on uncertainty, never retry."""
    try:
        _check_plan(rest, plan, expected_digest, now)
        deadline = monotonic() + (plan.expires_at - now).total_seconds()
        with rest.journal.lock():
            return await _apply_locked(rest, plan, deadline=deadline)
    except AdminError as exc:
        return AdminApplyResult(status="rejected", code=exc.code)
    except DiscordRestError:
        return AdminApplyResult(status="rejected", code="admin_snapshot_unavailable")
