package io.github.hexanomicon.lychd.companion.diagnostics

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.BatteryManager
import android.os.Build
import android.os.PowerManager
import android.os.StatFs
import android.os.SystemClock
import io.github.hexanomicon.lychd.companion.core.diagnostics.DeviceSnapshot
import io.github.hexanomicon.lychd.companion.core.diagnostics.Observation
import io.github.hexanomicon.lychd.companion.core.diagnostics.batteryPercent
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext

/** Bounded public API reads only. No capture, file scan, identifiers, permissions or network. */
internal class AndroidDeviceStatus(context: Context) {
    private val app = context.applicationContext

    suspend fun collect(): DeviceSnapshot = withContext(Dispatchers.IO) {
        ensureActive()
        val hardware = observe { app.packageManager.hasSystemFeature(PackageManager.FEATURE_MICROPHONE) }
        val permission = observe { app.checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED }
        val space = observe { StatFs(app.noBackupFilesDir.path).availableBytes.takeIf { it >= 0 } }
        val battery = observe { app.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED)) }
        val intent = (battery as? Observation.Known)?.value
        val level = if (intent == null) Observation.Unknown else batteryPercent(
            intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1), intent.getIntExtra(BatteryManager.EXTRA_SCALE, -1),
        )
        val charging = when (intent?.getIntExtra(BatteryManager.EXTRA_STATUS, -1)) {
            BatteryManager.BATTERY_STATUS_CHARGING, BatteryManager.BATTERY_STATUS_FULL -> Observation.Known(true)
            BatteryManager.BATTERY_STATUS_DISCHARGING, BatteryManager.BATTERY_STATUS_NOT_CHARGING -> Observation.Known(false)
            else -> Observation.Unknown
        }
        val saving = observe { app.getSystemService(PowerManager::class.java)?.isPowerSaveMode }
        ensureActive()
        DeviceSnapshot(SystemClock.elapsedRealtime(), Build.VERSION.SDK_INT, hardware, permission, space, level, charging, saving)
    }

    private fun <T : Any> observe(read: () -> T?): Observation<T> = try {
        read()?.let { Observation.Known(it) } ?: Observation.Unknown
    } catch (cancelled: CancellationException) {
        throw cancelled
    } catch (_: Exception) {
        Observation.Unknown
    }
}
