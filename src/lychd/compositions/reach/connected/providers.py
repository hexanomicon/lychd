"""Pure provider request plans for the candidate correspondence profile.

Routes are provider-qualified semantic routes, never URLs or transport authority.
The host must bind an admitted origin, credentials, fresh grants, finite response
budgets and current provider eligibility before any request. No builder performs
discovery, saves drafts remotely, acknowledges intake or claims delivery.
"""

from __future__ import annotations

import base64
import json
import re
from email import policy
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import format_datetime
from typing import Any, Literal, NoReturn, Protocol

from lychd.compositions.reach.connected.schemas import (
    ChatTarget,
    EmailTarget,
    ForgeTarget,
    PreparedOperation,
    PreparedRequest,
    ReadRequest,
    SendRequest,
    SocialTarget,
)

_JMAP_CORE = "urn:ietf:params:jmap:core"
_JMAP_MAIL = "urn:ietf:params:jmap:mail"
_JMAP_SUBMISSION = "urn:ietf:params:jmap:submission"
_GITHUB_REPOSITORY_PARTS = 2
_DISCORD_TEXT = 2000
_TELEGRAM_TEXT = 4096
_WHATSAPP_TEXT = 4096
_LINKEDIN_TEXT = 3000


class UnsupportedOperationError(ValueError):
    """The selected profile has no admitted protocol for this operation."""


def _refuse(reason: str) -> NoReturn:
    raise UnsupportedOperationError(reason)


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _plan(
    preparation: PreparedOperation,
    method: Literal["GET", "POST"],
    route: str,
    *,
    body: object | None = None,
    query: tuple[tuple[str, str], ...] = (),
    headers: tuple[tuple[str, str], ...] = (),
) -> PreparedRequest:
    return PreparedRequest(
        preparation=preparation,
        method=method,
        route=route,
        body="" if body is None else _json(body),
        query=query,
        headers=headers,
    )


def _numeric(value: str, *, signed: bool = False) -> str:
    pattern = r"-?[1-9][0-9]{0,19}" if signed else r"[1-9][0-9]{0,19}"
    if re.fullmatch(pattern, value) is None:
        msg = "invalid_numeric_id"
        raise ValueError(msg)
    return value


def _opaque(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]{1,255}", value) is None:
        msg = "invalid_provider_id"
        raise ValueError(msg)
    return value


def _page(request: ReadRequest) -> str:
    return "1" if request.cursor is None else _numeric(request.cursor)


def _mail_address(value: str) -> str:
    if not value.isascii() or any(character.isspace() for character in value):
        msg = "invalid_mail_address"
        raise ValueError(msg)
    try:
        address = Address(addr_spec=value)
    except ValueError as error:
        msg = "invalid_mail_address"
        raise ValueError(msg) from error
    if not address.username or not address.domain or address.addr_spec != value:
        msg = "invalid_mail_address"
        raise ValueError(msg)
    return value


def _mail_headers(request: SendRequest, target: EmailTarget) -> None:
    for value in (target.sender, *target.to, *target.cc, *target.bcc):
        _mail_address(value)
    if not target.to and not target.cc and not target.bcc:
        msg = "mail_recipient_required"
        raise ValueError(msg)
    if request.subject is None or any(character in request.subject for character in "\r\n\x00"):
        msg = "mail_subject_required_or_invalid"
        raise ValueError(msg)
    if (
        request.reply_to_id is not None
        and re.fullmatch(r"<[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+>", request.reply_to_id) is None
    ):
        msg = "invalid_mail_reply_id"
        raise ValueError(msg)


def _mime(preparation: PreparedOperation, request: SendRequest, target: EmailTarget) -> bytes:
    """Keep Bcc inside the sealed send MIME; Gmail derives its envelope from it."""
    _mail_headers(request, target)
    message = EmailMessage(policy=policy.SMTP)
    message["Date"] = format_datetime(preparation.prepared_at)
    message["From"] = target.sender
    for name, values in (("To", target.to), ("Cc", target.cc), ("Bcc", target.bcc)):
        if values:
            message[name] = ", ".join(values)
    message["Subject"] = request.subject
    message["Message-ID"] = f"<{preparation.digest}@reach.invalid>"
    if request.reply_to_id is not None:
        message["In-Reply-To"] = request.reply_to_id
        message["References"] = request.reply_to_id
    message.set_content(request.text, subtype="plain", charset="utf-8", cte="base64")
    return message.as_bytes()


class MailRequestBuilder(Protocol):
    """Mail family protocol with distinct Gmail and JMAP implementations."""

    def read(self, preparation: PreparedOperation, request: ReadRequest, target: EmailTarget) -> PreparedRequest: ...

    def send(self, preparation: PreparedOperation, request: SendRequest, target: EmailTarget) -> PreparedRequest: ...


class GmailRequestBuilder:
    """Credential-bound Gmail mailbox listing and direct sealed MIME submission."""

    def read(self, preparation: PreparedOperation, request: ReadRequest, target: EmailTarget) -> PreparedRequest:
        if target.mailbox_id != "me" or target.thread_id is not None:
            _refuse("gmail_read_requires_me_without_thread")
        query = (("maxResults", str(request.limit)), ("includeSpamTrash", "false"))
        if request.cursor is not None:
            query += (("pageToken", request.cursor),)
        return _plan(preparation, "GET", "gmail:/gmail/v1/users/me/messages", query=query)

    def send(self, preparation: PreparedOperation, request: SendRequest, target: EmailTarget) -> PreparedRequest:
        if target.mailbox_id != "me":
            _refuse("gmail_requires_me")
        body = {"raw": base64.urlsafe_b64encode(_mime(preparation, request, target)).decode("ascii").rstrip("=")}
        if target.thread_id is not None:
            if request.reply_to_id is None:
                _refuse("gmail_thread_requires_reply_headers")
            body["threadId"] = _opaque(target.thread_id)
        return _plan(preparation, "POST", "gmail:/gmail/v1/users/me/messages/send", body=body)


class FastmailRequestBuilder:
    """JMAP plans require a host-observed Session apiUrl, account and capabilities.

    Read returns only a bounded header/preview projection. Sending creates exact
    content then submits its creation reference; an existing mutable draft id is
    deliberately unavailable. HTTP success still requires method-level checking.
    """

    def read(self, preparation: PreparedOperation, request: ReadRequest, target: EmailTarget) -> PreparedRequest:
        if target.thread_id is not None:
            _refuse("jmap_thread_query_unsupported")
        position = 0 if request.cursor is None else int(_numeric(request.cursor))
        calls = [
            ["Email/query", {"accountId": target.mailbox_id, "limit": request.limit, "position": position}, "query"],
            [
                "Email/get",
                {
                    "accountId": target.mailbox_id,
                    "#ids": {"resultOf": "query", "name": "Email/query", "path": "/ids"},
                    "properties": ["id", "threadId", "from", "to", "cc", "bcc", "subject", "preview", "receivedAt"],
                },
                "get",
            ],
        ]
        return _plan(
            preparation, "POST", "fastmail:api", body={"using": [_JMAP_CORE, _JMAP_MAIL], "methodCalls": calls}
        )

    def send(self, preparation: PreparedOperation, request: SendRequest, target: EmailTarget) -> PreparedRequest:
        _mail_headers(request, target)
        if target.identity_id is None or target.draft_mailbox_id is None:
            _refuse("jmap_identity_and_draft_mailbox_required")
        if target.thread_id is not None:
            _refuse("jmap_thread_assignment_unsupported")
        email: dict[str, Any] = {
            "mailboxIds": {target.draft_mailbox_id: True},
            "keywords": {"$draft": True},
            "from": [{"email": target.sender}],
            "to": [{"email": value} for value in target.to],
            "cc": [{"email": value} for value in target.cc],
            "bcc": [{"email": value} for value in target.bcc],
            "subject": request.subject,
            "messageId": [f"{preparation.digest}@reach.invalid"],
            "textBody": [{"partId": "body", "type": "text/plain"}],
            "bodyValues": {"body": {"value": request.text}},
        }
        if request.reply_to_id is not None:
            email["inReplyTo"] = [request.reply_to_id[1:-1]]
            email["references"] = [request.reply_to_id[1:-1]]
        recipients = dict.fromkeys((*target.to, *target.cc, *target.bcc))
        calls = [
            ["Email/set", {"accountId": target.mailbox_id, "create": {"message": email}}, "create"],
            [
                "EmailSubmission/set",
                {
                    "accountId": target.mailbox_id,
                    "create": {
                        "submission": {
                            "identityId": target.identity_id,
                            "emailId": "#message",
                            "envelope": {
                                "mailFrom": {"email": target.sender},
                                "rcptTo": [{"email": value} for value in recipients],
                            },
                        }
                    },
                    "onSuccessUpdateEmail": {"#submission": {"keywords/$draft": None}},
                },
                "submit",
            ],
        ]
        return _plan(
            preparation,
            "POST",
            "fastmail:api",
            body={"using": [_JMAP_CORE, _JMAP_MAIL, _JMAP_SUBMISSION], "methodCalls": calls},
        )


def _mail(preparation: PreparedOperation, target: EmailTarget) -> PreparedRequest:
    provider = preparation.connection.provider
    builder: MailRequestBuilder
    if provider == "gmail":
        builder = GmailRequestBuilder()
    elif provider == "fastmail":
        if target.mailbox_id != preparation.connection.account_id:
            _refuse("jmap_account_mismatch")
        builder = FastmailRequestBuilder()
    else:
        _refuse("provider_family_mismatch")
    if target.sender != preparation.connection.actor_id:
        _refuse("mail_sender_mismatch")
    request = preparation.request
    return (
        builder.read(preparation, request, target)
        if isinstance(request, ReadRequest)
        else builder.send(preparation, request, target)
    )


def _reply(request: SendRequest, target: ChatTarget) -> str | None:
    if request.reply_to_id is not None and target.reply_to_id is not None and request.reply_to_id != target.reply_to_id:
        _refuse("reply_target_mismatch")
    return request.reply_to_id or target.reply_to_id


def _discord(preparation: PreparedOperation, target: ChatTarget) -> PreparedRequest:
    """Bind an exact channel request and nonce to its complete preparation."""
    channel = _numeric(target.conversation_id)
    route = f"discord:/api/v10/channels/{channel}/messages"
    request = preparation.request
    if isinstance(request, ReadRequest):
        query = (("limit", str(request.limit)),)
        if request.cursor is not None:
            query += (("before", _numeric(request.cursor)),)
        return _plan(preparation, "GET", route, query=query)
    if len(request.text) > _DISCORD_TEXT:
        _refuse("discord_text_limit")
    nonce = preparation.digest[:25]
    body: dict[str, Any] = {
        "content": request.text,
        "flags": 4,
        "allowed_mentions": {"parse": []},
        "nonce": nonce,
        "enforce_nonce": True,
    }
    reply = _reply(request, target)
    if reply is not None:
        body["allowed_mentions"]["replied_user"] = False
        body["message_reference"] = {"message_id": _numeric(reply), "channel_id": channel, "fail_if_not_exists": True}
    return _plan(preparation, "POST", route, body=body)


def _telegram(preparation: PreparedOperation, target: ChatTarget) -> PreparedRequest:
    """Bot send only; getUpdates is bot-wide and acknowledges offset advancement."""
    request = preparation.request
    if isinstance(request, ReadRequest):
        _refuse("telegram_target_read_unsupported")
    if len(request.text) > _TELEGRAM_TEXT:
        _refuse("telegram_text_limit")
    body: dict[str, Any] = {
        "chat_id": int(_numeric(target.conversation_id, signed=True)),
        "text": request.text,
        "link_preview_options": {"is_disabled": True},
    }
    reply = _reply(request, target)
    if reply is not None:
        body["reply_parameters"] = {"message_id": int(_numeric(reply))}
    return _plan(preparation, "POST", "telegram:/sendMessage", body=body)


def _whatsapp(preparation: PreparedOperation, target: ChatTarget) -> PreparedRequest:
    """Plan business freeform text only, never personal history or templates.

    A host must freshly establish registered business phone custody, recipient
    permission/opt-out, customer-service window, human escalation, current market
    and AI classification eligibility and spend budget. These values do not exist
    in this plan, so construction cannot establish transport eligibility.
    """
    request = preparation.request
    if isinstance(request, ReadRequest):
        _refuse("whatsapp_history_unsupported")
    if len(request.text) > _WHATSAPP_TEXT:
        _refuse("whatsapp_text_limit")
    phone = _numeric(preparation.connection.actor_id)
    body: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": _numeric(target.conversation_id),
        "type": "text",
        "text": {"preview_url": False, "body": request.text},
    }
    reply = _reply(request, target)
    if reply is not None:
        if re.fullmatch(r"wamid\.[A-Za-z0-9_=+-]{1,255}", reply) is None:
            _refuse("invalid_whatsapp_reply_id")
        body["context"] = {"message_id": reply}
    return _plan(preparation, "POST", f"whatsapp:/v26.0/{phone}/messages", body=body)


def _forge(preparation: PreparedOperation, target: ForgeTarget) -> PreparedRequest:
    """GitHub.com issue/PR timeline comments; no arbitrary hosts or code actions."""
    if preparation.connection.provider != "github":
        _refuse("forge_provider_unsupported")
    segments = target.repository.split("/")
    if len(segments) != _GITHUB_REPOSITORY_PARTS or any(
        re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,99}", value) is None or value in {".", ".."} for value in segments
    ):
        msg = "invalid_github_repository"
        raise ValueError(msg)
    route = f"github:/repos/{target.repository}/issues/{target.issue_number}/comments"
    headers = (("accept", "application/vnd.github+json"), ("x-github-api-version", "2026-03-10"))
    request = preparation.request
    if isinstance(request, ReadRequest):
        return _plan(
            preparation,
            "GET",
            route,
            query=(("per_page", str(request.limit)), ("page", _page(request))),
            headers=headers,
        )
    if request.reply_to_id is not None:
        _refuse("github_nested_reply_unsupported")
    return _plan(preparation, "POST", route, body={"body": request.text}, headers=headers)


def _social(preparation: PreparedOperation, target: SocialTarget) -> PreparedRequest:  # noqa: C901 - explicit provider-specific refusal paths
    """Organic authored text only; advertising and AI reply bots are separate effects."""
    request = preparation.request
    if isinstance(request, ReadRequest):
        _refuse("social_read_unsupported")
    if target.visibility != "public" or request.reply_to_id is not None:
        _refuse("social_requires_original_public_post")
    if target.account_id != preparation.connection.actor_id:
        _refuse("social_actor_mismatch")
    provider = preparation.connection.provider
    if provider == "facebook":
        if target.actor_kind != "page":
            _refuse("facebook_page_required")
        # Numeric ids alone cannot prove Page ownership; the profile and fresh host
        # grant must require a Page token/task. Personal-profile automation is absent.
        page = _numeric(target.account_id)
        return _plan(
            preparation, "POST", f"facebook:/v26.0/{page}/feed", body={"message": request.text, "published": True}
        )
    if provider == "linkedin":
        prefix = {"member": "person", "organization": "organization"}.get(target.actor_kind)
        if prefix is None or re.fullmatch(rf"urn:li:{prefix}:[A-Za-z0-9_-]{{1,100}}", target.account_id) is None:
            msg = "invalid_linkedin_author"
            raise ValueError(msg)
        commentary = "".join("\\" + char if char in r"\|{}@[]()<>#*_~" else char for char in request.text)
        # Conservatively bound the encoded little text in UTF-16 units as well
        # as ordinary ASCII characters; never split an admitted post.
        if len(commentary.encode("utf-16-le")) // 2 > _LINKEDIN_TEXT:
            _refuse("linkedin_text_limit")
        body: dict[str, Any] = {
            "author": target.account_id,
            # LinkedIn accepts `little` markup. Escape literal text before JSON
            # encoding so an apparent mention cannot become an attributed action.
            "commentary": commentary,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        return _plan(
            preparation,
            "POST",
            "linkedin:/rest/posts",
            body=body,
            headers=(("linkedin-version", "202610"), ("x-restli-protocol-version", "2.0.0")),
        )
    if provider == "x":
        if target.actor_kind != "user":
            _refuse("x_user_required")
        _numeric(target.account_id)
        return _plan(preparation, "POST", "x:/2/tweets", body={"text": request.text, "made_with_ai": True})
    _refuse("provider_family_mismatch")


def build_request(preparation: PreparedOperation) -> PreparedRequest:
    """Freeze one supported request without credentials, origins or external effects.

    Gmail listing contains ids, not unbounded message bodies. Telegram/WhatsApp
    history, Radicle, paid ads, personal-account automation, attachments and social
    replies have no request protocol in this candidate.
    """
    preparation = PreparedOperation.model_validate(preparation.model_dump())
    request = preparation.request
    connection = preparation.connection
    target = request.target
    if connection.profile_revision != "1":
        _refuse("unsupported_profile_revision")
    if isinstance(target, EmailTarget):
        return _mail(preparation, target)
    if isinstance(target, ChatTarget):
        if connection.provider == "discord":
            return _discord(preparation, target)
        if connection.provider == "telegram":
            return _telegram(preparation, target)
        if connection.provider == "whatsapp":
            return _whatsapp(preparation, target)
        _refuse("provider_family_mismatch")
    if isinstance(target, ForgeTarget):
        return _forge(preparation, target)
    return _social(preparation, target)
