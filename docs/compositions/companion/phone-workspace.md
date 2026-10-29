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
sync, and wider phone administration remain future candidate capabilities. Prove the initial
Bridge and voice foundation, then make the player useful and prove one admitted player action
and its failure endings on the S20 FE.

[Companion](index.md) · [Return](return.md) · [Choosing a Home](../choosing-a-home.md)
