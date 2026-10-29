package io.github.hexanomicon.lychd.companion.core.diagnostics

/** Local observations only: neither capability admission nor permission to perform an effect. */
sealed interface Observation<out T> {
    data class Known<T>(val value: T) : Observation<T>
    data object Unknown : Observation<Nothing>
}

data class DeviceSnapshot(
    val observedAtElapsedMillis: Long,
    val apiLevel: Int,
    val microphoneHardware: Observation<Boolean>,
    val microphonePermission: Observation<Boolean>,
    val availableAppFilesystemBytes: Observation<Long>,
    val batteryPercent: Observation<Int>,
    val charging: Observation<Boolean>,
    val powerSaveMode: Observation<Boolean>,
)

enum class DiagnosticRemedy { OPEN_APP_SETTINGS }

data class DiagnosticCheck(
    val title: String,
    val observation: String,
    val nextStep: String,
    val needsAttention: Boolean = false,
    val remedy: DiagnosticRemedy? = null,
)

private fun <T> Observation<T>.known(): T? = (this as? Observation.Known<T>)?.value

/** Modest local advice; no healthy/ready verdict follows from these readings. */
fun diagnose(snapshot: DeviceSnapshot): List<DiagnosticCheck> {
    val hardware = snapshot.microphoneHardware.known()
    val permission = snapshot.microphonePermission.known()
    val microphone = when {
        hardware == false -> DiagnosticCheck(
            "Microphone", "Android reports no microphone hardware.",
            "Use the words editor where offered. App permissions cannot add microphone hardware.", true,
        )
        hardware == null || permission == null -> DiagnosticCheck(
            "Microphone", "Microphone hardware or app permission could not be checked.",
            "Refresh device status. A missing reading does not establish working capture.", true,
        )
        !permission -> DiagnosticCheck(
            "Microphone", "Companion does not have microphone permission.",
            "Start recording where offered to request access, or review Companion's app permissions.",
            true, DiagnosticRemedy.OPEN_APP_SETTINGS,
        )
        else -> DiagnosticCheck(
            "Microphone", "Android reports microphone hardware and app permission granted.",
            "Capture has not been tested by this check. If recording fails, check Mic access, the audio route and other recording apps.",
        )
    }
    val available = snapshot.availableAppFilesystemBytes.known()?.takeIf { it >= 0 }
    val storage = when {
        available == null -> DiagnosticCheck(
            "App-data storage", "Available filesystem space could not be checked.", "Refresh status before a storage-dependent operation.", true,
        )
        available < LOW_STORAGE_BYTES -> DiagnosticCheck(
            "App-data storage", "${available / MIB} MiB available on the app-data filesystem.",
            "Space is below the 32 MiB advisory threshold. Review storage in Android before recording; this check deletes nothing.", true,
        )
        else -> DiagnosticCheck(
            "App-data storage", "${available / MIB} MiB available on the app-data filesystem.",
            "This is a filesystem reading, not a media inventory or a guarantee that a later write will succeed.",
        )
    }
    val percent = snapshot.batteryPercent.known()?.takeIf { it in 0..100 }
    val charging = snapshot.charging.known()
    val power = DiagnosticCheck(
        "Battery",
        listOf(percent?.let { "$it%" } ?: "Battery level unknown", when (charging) {
            true -> "charging or full"
            false -> "not charging"
            null -> "charging state unknown"
        }).joinToString(" · "),
        if (percent != null && percent <= LOW_BATTERY_PERCENT && charging != true)
            "Battery is low. Connect power before a long operation."
        else "This is the last reported battery state; refresh after conditions change.",
        percent == null || (percent <= LOW_BATTERY_PERCENT && charging != true),
    )
    val saving = when (snapshot.powerSaveMode.known()) {
        true -> DiagnosticCheck("Power saving", "Android power-save mode is enabled.",
            "Android may restrict background work. This observation does not diagnose a current playback or connection failure.", true)
        false -> DiagnosticCheck("Power saving", "Android power-save mode is disabled.",
            "Other Android or manufacturer background limits may still apply.")
        null -> DiagnosticCheck("Power saving", "Power-save mode could not be checked.", "Refresh status or inspect Android's battery settings.", true)
    }
    return listOf(microphone, storage, power, saving)
}

/** Invalid or missing platform battery extras stay unknown, rather than becoming zero. */
fun batteryPercent(level: Int, scale: Int): Observation<Int> =
    if (scale > 0 && level in 0..scale) Observation.Known((level.toLong() * 100 / scale).toInt())
    else Observation.Unknown

private const val MIB = 1024L * 1024
private const val LOW_STORAGE_BYTES = 32 * MIB
private const val LOW_BATTERY_PERCENT = 15
