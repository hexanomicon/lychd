---
title: Companion Access and Views
icon: material/shield-account-outline
---

# :material-shield-account-outline: Companion Access and Views

Companion presents the working interface authorized for the selected instance, human account,
work context and enrolled device. [IAM](../../adr/38-iam.md#profiles-and-working-interfaces)
already defines this rule. A profile or Role may influence Ward's decision; its name is not a
client permission. The mobile client never becomes the authority for User accounts, grants or
object ownership. [State of Work](../../state-of-the-work.md#remote-iam) owns the undelivered
remote IAM boundary.

## Views follow an authorized projection

An administrator, employee, household member or guest may receive different views, but these
labels alone select no screen. Two people with the same Role may be authorized for different
objects. One person may have different interfaces in personal and workplace instances. Human
identity, device/application identity, authentication session, Bridge conversation and Companion
session remain separate facts.

| Working view | Required current facts | When those facts are missing |
| --- | --- | --- |
| Connection and account choice | A locally supported enrollment/sign-in flow for the selected instance; no protected content before authentication. | Show connection/access status and public client information. The first fixture has no live enrollment or sign-in flow. |
| Applications and work contexts | Ward-filtered offered applications and individually permitted contexts. | Omit unavailable entries; do not download a global catalogue and filter private objects locally. |
| Conversation and results | Read access to each exact session/result and a compatible presentation profile. | Show a denied/unavailable state without retaining or fetching another person's history. |
| Words editor and submission | An offered submission action, its exact object/context, current authority and an allowed workflow state. | Read-only conversation may remain available; create/edit/review/send are separate decisions. |
| Voice capture and presentation | The relevant offered voice action, admitted privacy/custody policy, current device capabilities and Android permission/audio conditions. | Keep text where independently permitted. Microphone permission alone grants no host voice operation. |
| Local privacy and safety controls | Ownership of the current local effect or bytes. | Stop and discard stay callable even after work access disappears. |

Companion revision 3 excludes mobile administration and voice-only approval. Administrative
powers do not automatically expose Altar's operator instruments or grant access to all content.
A later administrative mobile product needs its own admitted contract and explicit Ward actions.
Workflow and action state also constrain controls: an allowed view cannot change a Scroll, resume
an Invocation, approve an effect or replay a submission by itself.

## First client implementation seam

The current `core` presentation policy is local offering logic with a closed screen/action
catalogue. It distinguishes unavailable access from an explicitly labelled development fixture.
It has no live Ward projection factory, role parser, Principal, Credential or Grant DTO. The
fixture's local offers can be narrowed in tests; the app exposes no user-controlled role or
capability selector.

The host-working surfaces are Conversation, Words and Local recording. Their actions remain separate:
creation/opening is distinct from reading/refreshing a conversation. A read-only offer therefore
cannot invoke the initial POST or Refresh's create fallback.

Local device status has its own foreground refresh lifecycle outside these offers. It reads only
bounded app/device conditions and can open this app's settings after a user click. It stays
available when host access is unavailable, without creating a conversation, requesting a
permission, capturing audio, or supplying remote authority. The
[local status contract](android-development.md#local-device-status) owns its observation limits.

Check the exact offer whenever work is requested. Missing policy denies work by default; an
omitted offer denies its corresponding surface/action. A stale local context cannot authorize
a callback or queued action. Also distinguish unknown access from an already attempted submission
whose external outcome is unknown.

Compose and its controller use the same policy. Hiding a button is presentation; the controller
also checks policy and local conditions before invoking transport or capture. This is preparation
for a future trusted projection adapter, not delivered server authorization. A local test can
assert that read-only offers cannot create/send and voice-disabled offers cannot record/replay;
it cannot establish Ward enforcement.

## Context change and loss of access

When the person selects another instance/account, signs out, loses access or replaces the current
projection, advance the local generation before any new work. Clear affected session IDs, history,
draft, reviewed-word state and pending presentation. Cancel local microphone/replay and attempt
bounded file cleanup.

Keep late transport and audio results bound to their originating generation; they cannot populate
the replacement context. Safety stops and deletion retries remain available so losing work access
does not prevent local cleanup.

Changing context does not cancel server work, transfer its authority or prove whether an
in-flight submission was admitted. Do not replay or retarget it. Reconciliation belongs to its
original context and exact retained request identity. Ordinary background invalidation can retain
one account's transient draft; explicit context loss must clear it. Reconnect requires fresh
authorization before receiving protected state or submitting work.

## Host integration still required

The host must first provide Ward enrollment for the human and device/application Principals,
then an authenticated, versioned mobile projection from the owning application. Its contract
needs the selected instance/account/context binding,
current credential/policy/revocation and device-capability generations, validity, offered views,
and actions bound to named objects and workflow states. Missing, unknown, expired or mismatched
facts refuse access. Only then should the generated mobile wire model be derived from its owning
host schema; a handwritten client model must not become that API by accident.

The host filters protected records in ownership-aware queries before delivery and rechecks
current authority at request/effect time. It must test two accounts, shared and unshared objects,
revocation, expiry, stale callbacks and instance switching. Authentication, UI projection and
authorization require distinct evidence. Current Bridge's fixed loopback Sigil and local Basic
credential supply none of this remote account boundary and must not be exposed over LAN/VPN.

[Companion](index.md) · [Android Development](android-development.md) · [Ward](../../sepulcher/extensions/ward.md)
