from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock, Mock

import discord
import pytest
from pydantic import ValidationError

from lychd.interface.discord.onboarding import (
    INTERESTS,
    Introduction,
    OnboardingPanel,
    OnboardingProfile,
    OnboardingService,
    _ConfirmationView,
    _IntroModal,
    _SelectionView,
)
from lychd.interface.discord.rest import DiscordRestError, EffectResult


def configured(*, elevated_human_role_ids: tuple[str, ...] = ()) -> OnboardingService:
    profile = OnboardingProfile(
        guild_id="300000000000000003",
        channel_id="400000000000000004",
        introduction_channel_id="400000000000000014",
        panel_message_id="700000000000000007",
        magus_role_id="600000000000000006",
        bot_role_id="800000000000000008",
        elevated_human_role_ids=elevated_human_role_ids,
    )
    rest = Mock(
        application_id="100000000000000001",
        bot_user_id="200000000000000002",
        guild_id=profile.guild_id,
    )
    rest.publish_introduction = AsyncMock(return_value=EffectResult(status="succeeded", remote_id="900000000000000009"))
    rest.ensure_member_role = AsyncMock()
    return OnboardingService(profile, rest)


def interaction(service: OnboardingService, *, private: bool = False) -> Any:
    value = Mock(spec=discord.Interaction)
    value.application_id = int(service.rest.application_id)
    value.guild_id = int(service.profile.guild_id)
    value.channel_id = int(service.profile.channel_id)
    value.id = 900000000000000009
    value.user = Mock(spec=discord.Member)
    value.user.id = 500000000000000005
    value.user.bot = False
    value.user.display_name = "Newcomer"
    value.user.guild = Mock(id=value.guild_id)
    value.message = Mock(spec=discord.Message)
    value.message.id = int(service.profile.panel_message_id)
    value.message.guild = Mock(id=value.guild_id)
    value.message.channel = Mock(id=value.channel_id)
    value.message.author = Mock(id=int(service.rest.bot_user_id), bot=True)
    value.message.webhook_id = None
    value.message.flags = Mock(ephemeral=private)
    value.response = Mock()
    value.response.is_done.return_value = False
    value.response.send_message = AsyncMock()
    value.response.edit_message = AsyncMock()
    value.response.send_modal = AsyncMock()
    value.response.defer = AsyncMock()
    value.edit_original_response = AsyncMock()
    return value


async def click(view: discord.ui.View, observed: Any, index: int) -> None:
    if await view.interaction_check(observed):
        await view.children[index].callback(observed)


def test_profile_rejects_everyone_or_colliding_roles_and_extra_fields() -> None:
    profile = configured().profile
    for patch in (
        {"magus_role_id": profile.guild_id},
        {"bot_role_id": profile.magus_role_id},
        {"contributor_role_id": "900000000000000009"},
    ):
        with pytest.raises(ValidationError):
            OnboardingProfile.model_validate({**profile.model_dump(), **patch})


def test_elevated_human_role_ids_are_optional_and_explicit() -> None:
    profile = configured().profile
    original = OnboardingProfile.model_validate(profile.model_dump(exclude={"elevated_human_role_ids"}))
    assert original.elevated_human_role_ids == ()
    elevated = ("900000000000000019", "900000000000000029")
    assert configured(elevated_human_role_ids=elevated).profile.elevated_human_role_ids == elevated


@pytest.mark.parametrize(
    "role_ids",
    [
        ("300000000000000003",),
        ("600000000000000006",),
        ("800000000000000008",),
        ("900000000000000019", "900000000000000019"),
        ("900000000000000019", "900000000000000029", "900000000000000039"),
        (900000000000000019,),
        (True,),
        ("not-a-discord-id",),
        ("18446744073709551616",),
        ["900000000000000019"],
        "900000000000000019",
        None,
    ],
)
def test_elevated_human_role_ids_reject_collisions_duplicates_and_coercion(role_ids: object) -> None:
    with pytest.raises(ValidationError):
        OnboardingProfile.model_validate({**configured().profile.model_dump(), "elevated_human_role_ids": role_ids})


def test_profile_requires_an_explicit_destination_separate_from_the_public_panel() -> None:
    profile = configured().profile
    with pytest.raises(ValidationError, match="introduction_channel_id"):
        OnboardingProfile.model_validate(profile.model_dump(exclude={"introduction_channel_id"}))
    with pytest.raises(ValidationError):
        OnboardingProfile.model_validate({**profile.model_dump(), "introduction_channel_id": profile.channel_id})


@pytest.mark.parametrize(
    "choices",
    [("Admin",), ("Contributor",), ("Maintainer",), ("Bot",), ("Magus",), ("hanging_around", "hanging_around")],
)
def test_only_stable_nonrole_choices_are_accepted(choices: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match="onboarding_introduction"):
        Introduction(choices)


def test_optional_multi_selection_and_intro_boundary() -> None:
    assert Introduction(()).interests == ()
    assert Introduction(tuple(INTERESTS), "x" * 400).intro == "x" * 400
    with pytest.raises(ValueError, match="onboarding_introduction"):
        Introduction((), "x" * 401)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind",
    [
        "guild",
        "member_guild",
        "channel",
        "introduction_channel",
        "application",
        "panel",
        "author",
        "webhook",
        "dm",
        "bot",
        "not_member",
        "message_guild",
        "message_channel",
    ],
)
async def test_public_panel_refuses_wrong_binding_before_opening_form(kind: str) -> None:
    service = configured()
    observed = interaction(service)
    mutations = {
        "guild": (observed, "guild_id", observed.guild_id + 1),
        "member_guild": (observed.user.guild, "id", observed.user.guild.id + 1),
        "channel": (observed, "channel_id", observed.channel_id + 1),
        "introduction_channel": (observed, "channel_id", int(service.profile.introduction_channel_id)),
        "application": (observed, "application_id", observed.application_id + 1),
        "panel": (observed.message, "id", observed.message.id + 1),
        "author": (observed.message.author, "id", observed.message.author.id + 1),
        "webhook": (observed.message, "webhook_id", 900000000000000009),
        "dm": (observed, "guild_id", None),
        "bot": (observed.user, "bot", True),
        "not_member": (observed, "user", Mock(spec=discord.User, id=500000000000000005, bot=False)),
        "message_guild": (observed.message.guild, "id", observed.message.guild.id + 1),
        "message_channel": (observed.message.channel, "id", observed.message.channel.id + 1),
    }
    target, attribute, value = mutations[kind]
    setattr(target, attribute, value)
    panel = OnboardingPanel(service)
    await click(panel, observed, 0)
    assert observed.response.send_message.await_args.kwargs["ephemeral"] is True
    assert "view" not in observed.response.send_message.await_args.kwargs
    service.rest.publish_introduction.assert_not_awaited()


@pytest.mark.asyncio
async def test_persistent_panel_opens_only_ephemeral_form_and_never_rewrites_public_panel() -> None:
    service = configured()
    observed = interaction(service)
    panel = OnboardingPanel(service)
    assert panel.is_persistent()
    await click(panel, observed, 0)
    sent = observed.response.send_message.await_args.kwargs
    assert sent["ephemeral"] is True
    selection = sent["view"]
    assert isinstance(selection, _SelectionView)
    select = selection.children[0]
    assert isinstance(select, discord.ui.Select)
    assert select.min_values == 0
    assert select.max_values == 3
    assert [option.value for option in select.options] == list(INTERESTS)
    observed.response.edit_message.assert_not_awaited()
    service.rest.publish_introduction.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["other_user", "expired", "public", "guild", "introduction_channel", "bot"])
async def test_private_confirmation_refuses_cross_user_expired_or_public_interactions(kind: str) -> None:
    service = configured()
    observed = interaction(service, private=True)
    view = _ConfirmationView(service, observed.user.id, time.monotonic() + 300, Introduction(()))
    if kind == "other_user":
        observed.user.id += 1
    elif kind == "expired":
        view.expires = time.monotonic() - 1
    elif kind == "public":
        observed.message.flags.ephemeral = False
    elif kind == "guild":
        observed.guild_id += 1
    elif kind == "introduction_channel":
        observed.channel_id = int(service.profile.introduction_channel_id)
    else:
        observed.user.bot = True
    await click(view, observed, 0)
    service.rest.publish_introduction.assert_not_awaited()
    assert observed.response.send_message.await_args.kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_selection_and_modal_do_not_publish_before_explicit_confirmation() -> None:
    service = configured()
    observed = interaction(service, private=True)
    view = _SelectionView(service, observed.user.id, time.monotonic() + 300)
    select = view.children[0]
    assert isinstance(select, discord.ui.Select)
    select._values = ["trying_it_out", "looking_to_contribute"]
    await click(view, observed, 0)
    await click(view, observed, 1)
    modal = observed.response.send_modal.await_args.args[0]
    assert isinstance(modal, _IntroModal)
    assert modal.intro.required is False
    assert modal.intro.max_length == 400
    modal.intro._value = "I build small tools."
    assert await modal.interaction_check(observed)
    await modal.on_submit(observed)
    args = observed.response.send_message.await_args
    assert args.kwargs["ephemeral"] is True
    assert args.args[0].startswith(f"Publish your introduction in <#{service.profile.introduction_channel_id}>?")
    assert service.profile.channel_id not in args.args[0]
    assert "Everyone who can read" in args.args[0]
    assert "updates your existing introduction" in args.args[0]
    confirmation = args.kwargs["view"]
    assert isinstance(confirmation, _ConfirmationView)
    assert confirmation.children[0].label == "Publish my introduction"
    service.rest.publish_introduction.assert_not_awaited()
    service.rest.ensure_member_role.assert_not_awaited()
    await click(confirmation, observed, 0)
    service.rest.publish_introduction.assert_awaited_once_with(
        service.profile.introduction_channel_id,
        "Meet Newcomer\nInterests: Trying it out, Looking to contribute.\nI build small tools.",
        subject_id=str(observed.user.id),
        event_id=str(observed.id),
    )
    assert str(observed.user.id) not in service.rest.publish_introduction.await_args.args[1]
    assert observed.response.defer.await_args.kwargs == {"ephemeral": True, "thinking": True}
    acknowledgement = observed.edit_original_response.await_args.kwargs["content"]
    assert f"<#{service.profile.introduction_channel_id}>" in acknowledgement
    service.rest.ensure_member_role.assert_not_awaited()
    await click(confirmation, observed, 0)
    assert service.rest.publish_introduction.await_count == 1


@pytest.mark.asyncio
async def test_selection_and_modal_refuse_interactions_from_the_publication_destination() -> None:
    service = configured()
    observed = interaction(service, private=True)
    observed.channel_id = int(service.profile.introduction_channel_id)
    selection = _SelectionView(service, observed.user.id, time.monotonic() + 300)
    await click(selection, observed, 1)
    observed.response.send_modal.assert_not_awaited()
    modal = _IntroModal(service, observed.user.id, time.monotonic() + 300, ())
    assert not await modal.interaction_check(observed)
    assert observed.response.send_message.await_args.kwargs["ephemeral"] is True
    assert "view" not in observed.response.send_message.await_args.kwargs
    service.rest.publish_introduction.assert_not_awaited()
    service.rest.ensure_member_role.assert_not_awaited()


@pytest.mark.asyncio
async def test_modal_revalidates_choices_and_intro_and_is_actor_bound() -> None:
    service = configured()
    observed = interaction(service, private=True)
    modal = _IntroModal(service, observed.user.id, time.monotonic() + 300, ())
    observed.user.id += 1
    assert not await modal.interaction_check(observed)
    observed.user.id -= 1
    modal.intro._value = "x" * 401
    with pytest.raises(ValueError, match="onboarding_introduction"):
        await modal.on_submit(observed)
    service.rest.publish_introduction.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancel_and_uncertain_effect_never_retry_publication() -> None:
    service = configured()
    observed = interaction(service, private=True)
    view = _ConfirmationView(service, observed.user.id, time.monotonic() + 300, Introduction(()))
    await click(view, observed, 1)
    service.rest.publish_introduction.assert_not_awaited()
    view = _ConfirmationView(service, observed.user.id, time.monotonic() + 300, Introduction(()))
    service.rest.publish_introduction.side_effect = DiscordRestError("network_error")
    await click(view, observed, 0)
    await click(view, observed, 0)
    assert service.rest.publish_introduction.await_count == 1
    assert "not confirmed" in observed.edit_original_response.await_args.kwargs["content"]


@pytest.mark.asyncio
async def test_role_assignment_is_independent_of_interests_and_cannot_assign_privileged_roles() -> None:
    service = configured(elevated_human_role_ids=("900000000000000019", "900000000000000029"))
    member = interaction(service).user
    # Names alone neither exempt a human nor become a baseline assignment target.
    member.roles = [
        Mock(id=900000000000000039, name="Contributor"),
        Mock(id=900000000000000049, name="Maintainer"),
        Mock(id=900000000000000059, name="Admin"),
    ]
    await service.ensure_base_role(member, event_id="900000000000000009")
    service.rest.ensure_member_role.assert_awaited_once_with(
        str(member.id), service.profile.magus_role_id, event_id="900000000000000009"
    )
    member.bot = True
    await service.ensure_base_role(member, event_id="900000000000000010")
    assert service.rest.ensure_member_role.await_args.args[1] == service.profile.bot_role_id
    member.guild.id += 1
    with pytest.raises(ValueError, match="onboarding_member_binding"):
        await service.ensure_base_role(member, event_id="900000000000000011")
    assert service.rest.ensure_member_role.await_count == 2
    service.rest.publish_introduction.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("role_id", ["900000000000000019", "900000000000000029"])
async def test_existing_elevated_human_role_skips_magus_without_grant_or_removal(role_id: str) -> None:
    service = configured(elevated_human_role_ids=("900000000000000019", "900000000000000029"))
    member = interaction(service).user
    member.roles = [Mock(id=int(role_id))]
    result = await service.ensure_base_role(member, event_id="900000000000000009")
    assert result == EffectResult(status="succeeded", code="community_role_present")
    service.rest.ensure_member_role.assert_not_awaited()
    service.rest.publish_introduction.assert_not_awaited()
    # Selection uses this observation, rather than retaining member-role state.
    member.roles = []
    await service.ensure_base_role(member, event_id="900000000000000010")
    service.rest.ensure_member_role.assert_awaited_once_with(
        str(member.id), service.profile.magus_role_id, event_id="900000000000000010"
    )


@pytest.mark.asyncio
async def test_bot_baseline_and_guild_binding_override_human_role_exemptions() -> None:
    service = configured(elevated_human_role_ids=("900000000000000019",))
    member = interaction(service).user
    member.roles = [Mock(id=900000000000000019)]
    member.bot = True
    await service.ensure_base_role(member, event_id="900000000000000009")
    service.rest.ensure_member_role.assert_awaited_once_with(
        str(member.id), service.profile.bot_role_id, event_id="900000000000000009"
    )
    member.bot = False
    member.guild.id += 1
    with pytest.raises(ValueError, match="onboarding_member_binding"):
        await service.ensure_base_role(member, event_id="900000000000000010")
    assert service.rest.ensure_member_role.await_count == 1
