# Companion Android Client

Native Kotlin/Compose development client for the [Companion Composition](../../docs/compositions/companion/index.md).
The debug app runs an explicitly labelled in-process Bridge fixture and records/replays bounded
local audio. It does not connect to a live LychD, transcribe, synthesize speech, or enroll a device.
Both debug and release also offer foreground local device status: microphone hardware/permission,
app-data filesystem space, battery/charging and power-save mode, with explicit troubleshooting
steps. These readings stay on the phone; Refresh neither requests access nor performs repairs.

## Build

Use JDK 17, Python 3.12+ and an Android SDK with `platforms;android-36` and `build-tools;36.0.0`.
Set `JAVA_HOME` and `ANDROID_HOME` to those installations, or configure `sdk.dir` in ignored
`local.properties`. Android Studio is optional. No NDK, Google account, Play Services, Firebase,
backend service, or model download is needed. The official Gradle wrapper checks the distribution
SHA-256; dependency versions live in `gradle/libs.versions.toml` and resolved versions in lockfiles.
Project configurations and buildscript classpaths use strict dependency locking: resolution fails
when its lock state is missing or inconsistent. The root `buildscript-gradle.lockfile` pins the
plugin dependency graph; module buildscript locks record their empty classpaths because the root
already supplies those plugins.
Artifact hashes live in `gradle/verification-metadata.xml`; they check integrity against this
initial build, not upstream authorship or an independently audited supply chain.

From this directory:

```bash
./gradlew :core:check :app:testDebugUnitTest :app:lintDebug :app:assembleDebug
```

The APK is `app/build/outputs/apk/debug/app-debug.apk`. Its application ID is
`io.github.hexanomicon.lychd.companion.dev`; Android generates a local debug signing key.
It requires Android 8.0/API 26 or newer, so the S20 FE's standard Android versions meet the API
floor. Actual Samsung microphone, lifecycle and headset behavior still requires a handset test.

With USB debugging enabled and your device explicitly authorized for ADB:

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

You can also transfer the APK yourself and allow installation for that transfer app in Android.
Release builds keep host work unavailable while allowing local device status; no production
signing or live transport is configured. Debug signing cannot be treated as a future production
identity.

Protocol and generator tests can run without an Android SDK:

```bash
./gradlew -PcoreOnly=true :core:check
```

Use `--offline` after dependencies and the wrapper distribution have been cached. Updating the
dependency graph deliberately uses `--write-locks` with the relevant check tasks; inspect the
resulting lockfile changes. To regenerate buildscript locks for every module, including the
optional prototype, run `./gradlew --write-locks -PincludeOfflineApp=true help`. This resolves the
existing plugin graph without building an APK; it does not regenerate ordinary module locks.

## Source

`app` owns Compose UI, ViewModel/lifecycle integration, testable handset interaction, Android
permission handling, AudioRecord and Media3 adapters. `core` owns bounded local Bridge interaction,
Ktor HTTP contract probes, local presentation policy and a separate local diagnostics model/monitor.
Android reads are in `app`; diagnostics refresh on foreground return or request and become stale
on background entry. Views and handlers consult the same
screen/action offers; unavailable policy offers no work. These local offers are a seam for a
future authorized host projection, not delivered Ward authentication or object grants.
The mock engine is the only transport engine in this slice; CIO remains a researched live-engine
candidate. The manifest has no Internet permission.
The merged APK also carries Media3's normal network-state/wake-lock declarations and AndroidX
component declarations; inspecting only the handwritten manifest does not inventory the APK.
The client code follows the repository's [MPL-2.0 license](../../LICENSE); library and SDK licenses
retain their own owners. This app does not supply source for Samsung firmware or modem code.

`tools/generate_wire.py` derives selected wire models, JSON token-shape checks and their reference closure from
[`clients/web/openapi.json`](../web/openapi.json) into `core/build/generated/wire`. Do not edit
generated Kotlin or create a mobile schema copy. Unsupported schema shapes fail generation;
semantic checks around decoded models remain client code. Standalone generator tests use only
Python's standard library.

[Android Development](../../docs/compositions/companion/android-development.md) owns this slice's
behavior, custody, test limits and next integration steps. [Android Foundation](../../docs/compositions/companion/android-foundation.md)
retains the broader construction study. [Access and Views](../../docs/compositions/companion/access-and-views.md)
owns the mobile application of IAM law; [State of Work](../../docs/state-of-the-work.md#companion-android-client)
owns delivery claims.

See [ADR 01](../../docs/adr/01-doctrine.md#repository-source-topology) for the client boundary.

## Offline text prototype

The independent `interaction` reducer and opt-in `offline` Android application preserve the
memory-only text draft experiment. They share this checkout's Gradle, Kotlin, Compose and JDK
versions. The existing `app` remains the foreground audio/mock-transport client described above.
The offline application has its own application ID, `org.lychd.companion.offline`, and declares
neither network nor microphone permission. It does not connect to the Vessel or persist drafts.

Run the reducer without an Android SDK:

```sh
./gradlew --no-daemon --dependency-verification=strict -PcoreOnly=true :interaction:test
```

With the Android SDK configured, build and test the separate prototype:

```sh
./gradlew --no-daemon --dependency-verification=strict -PcoreOnly=true -PincludeOfflineApp=true \
  :offline:testDebugUnitTest :offline:lintDebug :offline:assembleDebug :offline:assembleDebugAndroidTest
```

The [screen](offline/src/main/kotlin/org/lychd/companion/CompanionScreen.kt) and
[ViewModel](offline/src/main/kotlin/org/lychd/companion/OfflineDraftViewModel.kt) expose a draft's
fixed deadline, revision-fenced edits, expiry and local cancellation. Review and Submit remain
disabled. Activity recreation preserves the current process-local state; process death does not.
The [reducer](interaction/src/main/kotlin/org/lychd/companion/interaction/Interaction.kt) also models
inert review, submission and presentation transitions with exact process-local identity tokens.
No reducer signal is a native admission, destination effect or durable receipt.

The [unit tests](offline/src/test/kotlin/org/lychd/companion/OfflineDraftViewModelTest.kt) and
[instrumentation tests](offline/src/androidTest/kotlin/org/lychd/companion/CompanionLifecycleTest.kt)
keep JVM and device evidence separate. A device run uses `:offline:connectedDebugAndroidTest`
with an explicitly selected emulator or device; APK assembly alone does not qualify that boundary.
