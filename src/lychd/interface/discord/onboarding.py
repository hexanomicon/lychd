"""Optional guild-bound onboarding; private drafts never enter native execution."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Self

import discord
from pydantic import BaseModel, ConfigDict, model_validator

from lychd.interface.discord.rest import DiscordRest, DiscordRestError, EffectResult
from lychd.interface.discord.schemas import DiscordId

FORM_SECONDS = 300
MAX_INTRO_CHARS = 400
INTERESTS = {
    "hanging_around": "Hanging around",
    "trying_it_out": "Trying it out",
    "looking_to_contribute": "Looking to contribute",
}
_DENIED = "This onboarding control is unavailable here or has expired. Open a new form from start-here."


class OnboardingProfile(BaseModel):
    """Exact host-selected resources; role names and permissions require startup verification."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, hide_input_in_errors=True)

    guild_id: DiscordId
    channel_id: DiscordId
    panel_message_id: DiscordId
    magus_role_id: DiscordId
    bot_role_id: DiscordId

    @model_validator(mode="after")
    def separate_roles(self) -> Self:
        if self.magus_role_id == self.bot_role_id or self.guild_id in {self.magus_role_id, self.bot_role_id}:
            msg = "onboarding_role_binding"
            raise ValueError(msg)
        return self


@dataclass(frozen=True)
class Introduction:
    """An optional selection and bounded introduction, without member authority."""

    interests: tuple[str, ...]
    intro: str = ""

    def __post_init__(self) -> None:
        """Reject unknown interests and introduction text outside the admitted bound."""
        if (
            type(self.interests) is not tuple
            or any(type(value) is not str or value not in INTERESTS for value in self.interests)
            or len(set(self.interests)) != len(self.interests)
            or type(self.intro) is not str
            or len(self.intro) > MAX_INTRO_CHARS
        ):
            msg = "onboarding_introduction"
            raise ValueError(msg)

    def text(self, member: discord.Member | discord.User) -> str:
        """Render a concise text summary with no mention or user-controlled formatting."""

        def plain(value: str) -> str:
            return discord.utils.escape_mentions(discord.utils.escape_markdown(" ".join(value.split())))

        name = plain(str(member.display_name).strip()[:80]) or "Community member"
        choices = (
            ", ".join(label for key, label in INTERESTS.items() if key in self.interests) or "No interests selected"
        )
        text = f"Meet {name}\nInterests: {choices}."
        if self.intro.strip():
            text += f"\n{plain(self.intro)}"
        return text


async def _notice(interaction: discord.Interaction, text: str) -> None:
    """Acknowledge a refusal without exception or interaction payload diagnostics."""
    if not interaction.response.is_done():
        await interaction.response.send_message(text, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())


class OnboardingService:
    """Bind UI admission and the existing journaled single-attempt REST adapter."""

    def __init__(self, profile: OnboardingProfile, rest: DiscordRest) -> None:
        """Bind one explicit profile to the authenticated adapter for the same guild."""
        if profile.guild_id != rest.guild_id:
            msg = "onboarding_guild_binding"
            raise ValueError(msg)
        self.profile = profile
        self.rest = rest

    def member_allowed(self, member: object) -> bool:
        return isinstance(member, discord.Member) and str(member.guild.id) == self.profile.guild_id

    def allowed(self, interaction: discord.Interaction) -> bool:
        return (
            str(interaction.application_id) == self.rest.application_id
            and str(interaction.guild_id) == self.profile.guild_id
            and str(interaction.channel_id) == self.profile.channel_id
            and self.member_allowed(interaction.user)
            and not interaction.user.bot
        )

    def panel_allowed(self, interaction: discord.Interaction) -> bool:
        message = interaction.message
        return (
            self.allowed(interaction)
            and message is not None
            and str(message.id) == self.profile.panel_message_id
            and message.guild is not None
            and str(message.guild.id) == self.profile.guild_id
            and str(message.channel.id) == self.profile.channel_id
            and str(message.author.id) == self.rest.bot_user_id
            and message.author.bot
            and message.webhook_id is None
        )

    async def ensure_base_role(self, member: discord.Member, *, event_id: str) -> EffectResult:
        """Assign only the configured baseline role, independently of all UI interests."""
        if not self.member_allowed(member):
            msg = "onboarding_member_binding"
            raise ValueError(msg)
        role_id = self.profile.bot_role_id if member.bot else self.profile.magus_role_id
        return await self.rest.ensure_member_role(str(member.id), role_id, event_id=event_id)


class _PrivateView(discord.ui.View):
    def __init__(self, service: OnboardingService, actor_id: int, expires: float) -> None:
        super().__init__(timeout=max(0.1, expires - time.monotonic()))
        self.service = service
        self.actor_id = actor_id
        self.expires = expires

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        allowed = (
            self.service.allowed(interaction)
            and interaction.user.id == self.actor_id
            and time.monotonic() < self.expires
            and interaction.message is not None
            and interaction.message.flags.ephemeral
        )
        if not allowed:
            await _notice(interaction, _DENIED)
        return allowed

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item[Any]) -> None:
        del error, item
        await _notice(interaction, "The form could not be completed. Open a new form from start-here.")


class OnboardingPanel(discord.ui.View):
    """Register this persistent view against the exact existing welcome message at startup."""

    def __init__(self, service: OnboardingService) -> None:
        """Create the persistent public entry control for this configured guild."""
        super().__init__(timeout=None)
        self.service = service

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not self.service.panel_allowed(interaction):
            await _notice(interaction, _DENIED)
            return False
        return True

    @discord.ui.button(
        label="Introduce yourself", style=discord.ButtonStyle.primary, custom_id="lychd:onboarding:open:v1"
    )
    async def open_form(self, interaction: discord.Interaction, button: discord.ui.Button[Self]) -> None:
        del button
        await interaction.response.send_message(
            "Choose any interests, or leave them empty. Your choices are private until you explicitly publish.",
            ephemeral=True,
            view=_SelectionView(self.service, interaction.user.id, time.monotonic() + FORM_SECONDS),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item[Any]) -> None:
        del error, item
        await _notice(interaction, "The form could not be opened. Try again later.")


class _SelectionView(_PrivateView):
    def __init__(self, service: OnboardingService, actor_id: int, expires: float) -> None:
        super().__init__(service, actor_id, expires)
        self.interests: tuple[str, ...] = ()
        self.advanced = False

    @discord.ui.select(
        placeholder="Optional interests (choose any)",
        min_values=0,
        max_values=3,
        options=[discord.SelectOption(label=label, value=key) for key, label in INTERESTS.items()],
    )
    async def interests_selected(self, interaction: discord.Interaction, select: discord.ui.Select[Self]) -> None:
        draft = Introduction(tuple(select.values))
        self.interests = draft.interests
        await interaction.response.defer()

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.primary)
    async def continue_form(self, interaction: discord.Interaction, button: discord.ui.Button[Self]) -> None:
        del button
        if self.advanced:
            await _notice(interaction, "This form has already continued. Open a new form from start-here.")
            return
        self.advanced = True
        self.stop()
        await interaction.response.send_modal(_IntroModal(self.service, self.actor_id, self.expires, self.interests))


class _IntroModal(discord.ui.Modal, title="Optional introduction"):
    intro: discord.ui.TextInput[Self] = discord.ui.TextInput(
        label="A little about yourself (optional)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=MAX_INTRO_CHARS,
    )

    def __init__(self, service: OnboardingService, actor_id: int, expires: float, interests: tuple[str, ...]) -> None:
        super().__init__(timeout=max(0.1, expires - time.monotonic()))
        self.service = service
        self.actor_id = actor_id
        self.expires = expires
        self.interests = interests
        self.submitted = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        allowed = (
            self.service.allowed(interaction)
            and interaction.user.id == self.actor_id
            and time.monotonic() < self.expires
        )
        if not allowed:
            await _notice(interaction, _DENIED)
        return allowed

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if self.submitted:
            await _notice(interaction, "This introduction is already awaiting confirmation.")
            return
        draft = Introduction(self.interests, self.intro.value)
        self.submitted = True
        # SDK modal values are private until this separate, explicit confirmation.
        await interaction.response.send_message(
            "Publish your introduction in start-here? Everyone who can read that channel can see it. If you have already introduced yourself, this updates your existing introduction.\n\n"
            + draft.text(interaction.user),
            ephemeral=True,
            suppress_embeds=True,
            allowed_mentions=discord.AllowedMentions.none(),
            view=_ConfirmationView(self.service, self.actor_id, self.expires, draft),
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        del error
        await _notice(interaction, "The form could not be completed. Open a new form from start-here.")


class _ConfirmationView(_PrivateView):
    def __init__(self, service: OnboardingService, actor_id: int, expires: float, draft: Introduction) -> None:
        super().__init__(service, actor_id, expires)
        self.draft = draft
        self.attempted = False

    @discord.ui.button(label="Publish my introduction", style=discord.ButtonStyle.primary)
    async def publish(self, interaction: discord.Interaction, button: discord.ui.Button[Self]) -> None:
        del button
        if self.attempted:
            await _notice(interaction, "This form has already been submitted. It will not publish again.")
            return
        self.attempted = True
        self.stop()
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            result = await self.service.rest.publish_introduction(
                self.service.profile.channel_id,
                self.draft.text(interaction.user),
                subject_id=str(interaction.user.id),
                event_id=str(interaction.id),
            )
            if result.status == "succeeded":
                text = "Your introduction was published."
            elif result.status == "rejected" and result.code is not None and result.code.startswith("http_4"):
                text = "Your introduction could not be published. You can open a new form and try again later."
            else:
                text = "Publication was not confirmed. Do not submit again until an operator checks the public channel."
        except (ValueError, OSError, TimeoutError, DiscordRestError):
            text = "Publication was not confirmed. Do not submit again until an operator checks the public channel."
        await interaction.edit_original_response(
            content=text, view=None, allowed_mentions=discord.AllowedMentions.none()
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button[Self]) -> None:
        del button
        if self.attempted:
            await _notice(interaction, "This form has already been submitted or cancelled.")
            return
        self.attempted = True
        self.stop()
        await interaction.response.edit_message(content="Introduction cancelled. Nothing was published.", view=None)
