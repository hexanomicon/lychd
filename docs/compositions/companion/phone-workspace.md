---
title: Companion Phone Workspace
icon: material/cellphone-cog
---

# :material-cellphone-cog: Companion Phone Workspace

Companion could grow into the everyday mobile workspace through which LychD can act on the
operator's phone. [Android Foundation](android-foundation.md) now places Bridge and foreground
voice first. The first everyday local feature remains an ordinary offline music player. Selected
photos and explicit file sync follow; a local Wi-Fi connection comes before access through a VPN.
Each stage adds named capabilities that the operator can grant and revoke on the phone.

This candidate study, opened **2026-10-07**, explores that direction beside
[`companion.mobile` revision `3`](index.md). It publishes no successor revision or supported phone
administration path. [State of Work](../../state-of-the-work.md#composition-portfolio-delivery)
owns delivery. The initial device to test is the operator's Samsung S20 FE; the first application
design requires ordinary Android app permissions rather than root or a replacement ROM.

## Start with a player worth using

The first screen is a folder-based music library, with albums and search as other ways into the
same files. Selecting a track starts playback and exposes the queue, pause, previous, next, seek,
repeat, and shuffle. Playback, library browsing, and queue changes remain useful without a host,
network connection, or model. An agent can later use those same explicit player operations.

The native Android client stays under `clients/android/**`, following Companion's Kotlin and
Jetpack Compose target. Android's [Media3 background playback](https://developer.android.com/media/media3/session/background-playback)
provides a concrete implementation route for a player session with system controls, headset
interaction, and playback while the screen is locked. Those behaviors still need testing on the
actual handset. Persistent offline music must not depend on an expendable thumbnail or download
cache.

A granted control session can permit playback operations without another prompt for every pause
or next track. Microphone capture, photo access, transfers, camera capture, and deletion have
separate permission and authority boundaries. The phone always exposes local stop and a way to
revoke remote control.

## Grow in useful stages

Feature development and connectivity are separate tracks: local music can work before remote
admission exists, and photos need no VPN to become useful.

| Stage | Proposed behavior | Smallest useful journey |
| --- | --- | --- |
| Local music | Folder library, search, queue, and offline/background playback. | Pick an album, lock the screen, use headset controls, and continue playing without LychD. |
| Paired Wi-Fi | Connect to the operator's host and admit bounded player operations. | Grant playback control, execute one identified request, and display the observed player state. |
| Selected photos | Browse selected images and prepare a copy to a chosen destination. | Select a photo, inspect what will leave the phone, and copy it without changing the original. |
| Explicit sync | Copy selected music from host to phone and selected photos from phone to host. | Interrupt a transfer, resume it, verify the complete file, and show the result. |
| VPN reach | Reach the same paired application service through a private route. | Repeat an admitted operation away from home with the same application identity and grants. |

Photo selection begins with Android's [system photo picker](https://developer.android.com/training/data-storage/shared/photo-picker).
A later custom gallery can request a wider collection explicitly. Selected URI access, copying
bytes, and camera permission are different capabilities; revoked access or a missing file must
be visible. File arrival does not itself authorize model analysis, memory ingestion, or training.

## Connect to the same LychD

The operator's intended experience is one selected LychD whether a request starts on the PC or
phone. Both devices can be request surfaces and, for admitted capabilities, execution targets.
The table describes the candidate behavior, not delivered cross-device access:

| Request starts on | Effect belongs on | Example |
| --- | --- | --- |
| PC | PC | Build and verify an application candidate on the workstation. |
| Phone | PC | Request that same build or another admitted host workflow from the mobile client. |
| PC | Phone | Control an admitted player, deliver a reviewed APK, or request selected photo export. |
| Phone | Phone | Use offline playback and local status, or perform an explicitly admitted local operation. |

Every effect keeps its exact target, application, account/context and current authority. Changing
screens cannot retarget an admitted request, and pairing does not grant every capability in both
directions. Each device may refuse work locally. Local phone features remain useful when the PC
is unavailable; the phone does not need a second complete LychD installation to provide them.

The Linux host remains the place for LychD's domain records, workflows, and any heavier inference.
The phone owns its platform integration and bounded local interaction state. Local inference is
an optional later capability to measure on the actual device; it is no prerequisite for a usable
player or an authenticated host connection.

Wi-Fi supplies reachability. Pairing must establish the expected host and the phone application's
identity over an authenticated, encrypted connection. Discovery, an IP address, or membership of
the home network grants no application authority. Android network permissions also belong to the
device capability check; the [LAN permission guidance](https://developer.android.com/privacy-and-security/local-network-permission)
depends on the platform and target SDK.

The first remote path needs a protected mobile ingress with
[Ward](../../sepulcher/extensions/ward.md)-owned enrollment, scoped grants, and revocation. The
current same-host loopback service is not this path: the study does not authorize exposing or
tunnelling the current Altar. [Remote IAM](../../state-of-the-work.md#remote-iam) retains that
delivery boundary. Later, [Tether](../../sepulcher/extensions/tether.md) can supply VPN reachability
without replacing application authentication or widening the grants.

## Keep execution and ownership explicit

Companion presents the session, permissions, configuration, pending work, results, and reconnect
state. [Familiar](../familiar/index.md) supplies the exact phone capability snapshot, local limits,
and stop/refusal path. Ward owns identity and authority; Tether owns a later private route.

The player feature maintains its local file index, queue, and observed playback state. Android
storage and the selected locations retain custody of the media bytes. An execution request needs
an identified operation, target, current grant, expiry, and a result grounded in what the device
actually did. A model's request is not evidence that playback or a transfer happened.

Broader mobile execution exceeds Companion revision 3's current handoff/presentation contract.
Before admitting that path, [Choosing a Home](../choosing-a-home.md) must resolve the media and
transfer application ownership, then publish the appropriate accepted contract. This study does
not choose a new Composition or Suite merely because the client has several screens. Coordinating
multiple live Composition Invocations would need the separately owned Suite boundary.

## Build an app and put it on the phone

“Build me an MP3 player and put it on my phone” tests more than remote playback. The journey
starts with software construction and ends with observed installation and useful offline work.
It should work whether the request starts on the PC or phone; the selected destination and current
authority determine where each operation can happen.

[Android Foundation](android-foundation.md#growing-into-phone-capabilities-and-more-apps)
distinguishes a compiled Companion feature, another owned Android application, a host package and
an external service. Start the local player in the existing native project. An independently
requested app may reuse its library modules, but receives its own package, signing identity and
permissions. The existing foreground recording replay adapter does not supply a background music
service or durable library.

| Handoff | What must be retained | What establishes completion |
| --- | --- | --- |
| Request to candidate | Intended behavior, exact source bytes including admitted dirty inputs, build variant, tools, dependency closure, tests and permission changes | Reviewed candidate and observed check results; the current native Creation investigation does not execute this construction |
| Candidate to APK | Exact artifact digest and size, package/version, minimum SDK, signing identity and declared permissions | Verified signed APK; signing-key material stays outside the build report and ordinary worker workspace |
| APK to phone | Selected device and receiving location, exact artifact, transfer authority, expiry and storage bounds | Complete received bytes verified before staging; transfer alone does not establish installation |
| Staged APK to installation | Exact staged artifact, expected installed package/version/signer, local review and owned Android install session | Android terminal outcome and installed-identity readback, with ambiguity retained |
| Installation to useful app | Actual handset/OS, selected music folder, playback and interruption conditions | MP3 playback without a host or network, including locked-screen and headset behavior |

An operator campaign can first transfer the APK manually or through an explicitly authorized
[KDE Connect](https://kdeconnect.kde.org/) connection. That proves a delivery road without
claiming native mobile enrollment or remote control. The campaign must verify that the chosen
channel is actually available. [ADB wireless debugging](https://developer.android.com/tools/adb)
is a separate development profile with workstation pairing and much broader device access; it
does not become Companion enrollment.

This player-delivery pilot can run independently of the Bridge and Voice release. It proves
neither that release's live conversation nor an autonomous “ask, build, install” workflow.
[SDLC](../../adr/16-sdlc.md) governs the candidate handoffs; standalone Android app installation
does not inherit Core Evolution's body-update protocol. A future native construction/delivery
promise still needs its exact executable owners and contracts.

## Request the missing authority at the right boundary

An agent proposes a named operation against selected objects. Missing authority produces a
bounded request explaining that operation and its consequences. Acceptance may establish an
eligible standing grant, authorize one exact effect, or lead to Android's own permission screen.
It never turns a natural-language instruction into a general shell or device-administration grant.

| Boundary | Example | Authority that must exist |
| --- | --- | --- |
| Application access | Control the admitted player or copy selected files | Current Ward action/object grant, purpose, device binding and expiry |
| Android data access | Read a selected music folder or selected photo | Current platform permission or URI grant, checked on the phone before access |
| Package installation | Install the reviewed APK | Allowed installer source, exact local review and Android installation flow |
| Cleanup | Trash selected local media after verified export | Fresh exact cleanup review, current application authority and the applicable system request |
| Developer or managed device | Install through ADB or device-owner facilities | Separately enabled and revocable development/management posture with its own scope and evidence |

[IAM](../../adr/38-iam.md) owns grants and revocation; [HitL](../../adr/25-hitl.md) owns exact-call
consent. Secret/authority changes and destructive deletion retain their live-only boundary. Local
stop and access revocation stay available. A grant cannot manufacture a missing Android capability,
and revocation cannot retract exported bytes or prove cancellation of an already accepted OS job.
[Privilege](../../adr/10-privilege.md) supplies the closed-effect design rule; its Linux Host Reactor
transition word is not a phone operation protocol.

For a future ordinary-app installer, Android's
[per-source installation access](https://developer.android.com/reference/android/content/pm/PackageManager#canRequestPackageInstalls())
and `REQUEST_INSTALL_PACKAGES` declaration are distinct from Ward enrollment. Use an owned
[PackageInstaller session](https://developer.android.com/reference/android/content/pm/PackageInstaller.Session)
and explicitly require user action where the API supports it. Retain the session before commit
and handle pending user action. Unexpected package, version or signing changes require a new
review; a signing conflict must not trigger uninstall. Installation readback proves observed
package identity, not an independent hash of the installed raw APK bytes. Android documents narrow
[update exceptions](https://developer.android.com/reference/android/content/pm/PackageInstaller.SessionParams#setRequireUserAction(int));
this candidate's default keeps local confirmation.

The future operation record must bind operation/version, canonical request digest, initiating
account and device, target device/object, current grant and capability generations, exact content
or reviewed item set, expiry, local/platform attempt identity and observed outcome. These are
requirements for the receiving owner's contract, not a published DTO or universal execute API.
The phone adapter needs recoverable attempt evidence; Companion's screen must not become the
owner of application authorization or durable backup/cleanup judgment.

## Export photos, then review cleanup

“Get these photos onto my PC” begins with an explicit selection, destination and purpose. Retain
the representation actually read from each provider, its size and digest, and verify the committed
destination bytes. A picker can return cloud media; selected read access does not establish a
local original that the app can delete. A claim of original-byte backup needs evidence that the
provider supplied that representation. Export alone supplies no analysis or training permission.

“Free space after backing these up” is another operation. Prepare a fresh review of exact eligible
local items linked to verified export receipts. Recheck source identity, accessible content and
available version/generation information, destination custody, and current grants. A changed item,
unavailable original, failed backup or missing access cannot silently join the cleanup set.

The first cleanup experiment uses Android's API-30+
[trash request](https://developer.android.com/reference/android/provider/MediaStore#createTrashRequest(android.content.ContentResolver,%20java.util.Collection%3Candroid.net.Uri%3E,%20boolean))
for specific local MediaStore item URIs, with system confirmation and per-item observation.
Record the available restore window; trash eventually expires. Unsupported Android versions or
unresolvable picker/cloud items need an explicit unavailable result or system-gallery handoff.
Permanent deletion remains a separately reviewed operation, beyond this first experiment.

The platform request names item URIs, not expected content hashes. Another app may edit an item
while confirmation is pending. This design therefore cannot promise atomic deletion of exactly
the backed-up bytes. Report verified exported representations and observed trashed item identities
separately. Loss of read access alone proves neither trash nor deletion.

## Cases that should shape the next increment

| Request | Useful finish | Failure that must remain visible |
| --- | --- | --- |
| Build and deliver a player | Reviewed APK installed on the selected phone; local MP3 works offline | Changed signer, denied installation, lost outcome or unusable locked-screen playback |
| Bring selected photos to the PC | Each selected representation committed and verified; originals retained | Revoked URI, unavailable cloud provider, full destination or partial copy |
| Recover phone space | Exact reviewed local items observed in trash, with linked export receipts and restore window | Changed source, declined confirmation, expired access or unknown item outcome |
| Prepare offline travel music | Selected files and a desired queue usable in airplane mode | Insufficient storage, destination conflict or reconnect duplicating a queue edit |
| Attach field material to a case | Reviewed capture transferred, then separately admitted by the destination | Transfer succeeding while destination admission fails |
| Replace a lost phone | Old enrollment revoked; new body admitted and permitted content restored | Old callbacks or copied credentials entering the replacement context |

Keep two implementation tracks explicit. The local track builds on the implemented review/context fencing, proves
the folder player, and exercises reviewed APK delivery through an external operator channel. The
native connection track first resolves the operation/material owner, then closes protected ingress,
enrollment, exact request lookup and one bounded phone effect. Add verified photo export before
the separate trash experiment. Voice and later VPN can use those admitted boundaries when their
own release requirements pass; neither supplies missing phone-operation authority.

The strongest reason to stop expanding Companion is a materially different durable lifecycle:
backup retention, transfer recovery or cleanup judgment may need an application owner beyond a
device session. Apply [Choosing a Home](../choosing-a-home.md) at that seam. Familiar may admit a
phone-specific controller and stop policy without absorbing that application's records. The
accepted result must precede a production schema, endpoint or remote handler.

## Grow observation into troubleshooting

The broader request is a configurable mobile companion that gradually integrates with useful
phone functions, can inspect their state, and can help diagnose failures. The MP3 example is one
test case for that direction; independently requested Android applications remain part of the
construction/delivery goal. Local diagnostics are the first observation surface, while remote
inspection and repair still need their own admitted contracts.

For every added feature, distinguish implemented operation/version, observed device support,
Android access, current application authority, and the required user decision. Keep unavailable,
unknown, stale, denied and failed conditions visible. An observed capability is not an offered
operation, and an offered operation is not permission to perform every effect with it.

The proposed troubleshooting passage is:

1. Read bounded, relevant observations with their source, target and freshness.
2. Explain the evidence and uncertainty; distinguish a likely cause from a verified cause.
3. Propose a specific next check or repair, including its selected objects and consequences.
4. Obtain any missing eligible grant or exact live/system decision, then recheck it at effect time.
5. Perform the bounded operation and observe its result; preserve failure, partial or unknown
   outcomes and the recovery path.

A model may help interpret observations or prepare a proposal. It cannot invent a device state,
grant permission, or turn a suggestion into evidence of repair. Read-only status must not start
capture, export data, delete files, alter settings, install packages, or retry an unknown effect.
Low-risk actions may use explicitly eligible standing policy; Android and live-only gates retain
their own requirements. New sensors, media, notifications, background work and deeper system
integration must each earn a concrete capability, access and lifecycle boundary.

## Copy first, recover honestly

Initial sync is an explicit copy with selected source, destination, direction, size/storage
limits, and content identity. Partial bytes stay incomplete until verification and final commit.
Conflicts, insufficient space, missing access, and failed transfers remain visible. Both originals
survive; mirroring, overwrite, deletion, and cleanup need separately designed operations.

If an action response is lost, reconcile the device's operation record and current state before
claiming its outcome. Reconnect queries that identity instead of repeating a queue change or
another effect. Until reconciliation succeeds, the outcome remains unknown.

A transfer may resume its verified portions only under current access and grants; retry cannot
preserve expired or revoked authority. Network-dependent agent commands do not silently execute
when connectivity returns. The offline player continues independently.

The first device fixture should prove offline playback, locked-screen and headset behavior,
rejection of an unpaired peer on the same Wi-Fi, revocation, and lost acknowledgement without a
duplicate queue change. The photo/sync fixture then adds revoked URI access, an interrupted copy,
integrity verification, storage exhaustion, and a destination conflict with both originals intact.
VPN acceptance repeats the existing authenticated journey over another route.

Continuous observation, camera capture, notification actions, launcher integration, destructive
sync, and wider phone administration remain future candidate capabilities. The independent
player-delivery pilot can establish local usefulness while the Bridge and Voice release follows
its own acceptance sequence. Native phone control still needs one admitted player action and its
failure endings on the S20 FE.

[Companion](index.md) · [Return](return.md) · [Choosing a Home](../choosing-a-home.md)
