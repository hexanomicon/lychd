package io.github.hexanomicon.lychd.companion.core.diagnostics

import java.io.IOException
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.withContext
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class DeviceStatusMonitorTest {
    @Test fun samplingRequiresForegroundButNoHostPolicyOrTransport() = runTest {
        var reads = 0
        val monitor = DeviceStatusMonitor(this) { snapshot(++reads) }
        monitor.refresh()
        runCurrent()
        assertEquals(0, reads)
        assertNull(monitor.state.value.snapshot)
        assertTrue(monitor.state.value.stale)
        monitor.onForeground()
        assertTrue(monitor.state.value.refreshing)
        runCurrent()
        assertEquals(1, reads)
        assertEquals(snapshot(1), monitor.state.value.snapshot)
        assertFalse(monitor.state.value.stale)
        monitor.refresh()
        runCurrent()
        assertEquals(2, reads)
        assertEquals(snapshot(2), monitor.state.value.snapshot)
        monitor.close()
    }

    @Test fun backgroundRetainsTheLastReadingAsStaleAndSuppressesExplicitRefresh() = runTest {
        var reads = 0
        val monitor = DeviceStatusMonitor(this) { snapshot(++reads) }
        monitor.onForeground()
        runCurrent()
        monitor.onBackground()
        assertEquals(snapshot(1), monitor.state.value.snapshot)
        assertTrue(monitor.state.value.stale)
        assertFalse(monitor.state.value.refreshing)
        monitor.refresh()
        runCurrent()
        assertEquals(1, reads)
        monitor.close()
    }

    @Test fun resumeReadsPermissionAgainInsteadOfReusingTheGrantedSnapshot() = runTest {
        var permission = true
        var reads = 0
        val monitor = DeviceStatusMonitor(this) {
            snapshot(++reads).copy(microphonePermission = Observation.Known(permission))
        }
        monitor.onForeground()
        runCurrent()
        assertEquals(Observation.Known(true), monitor.state.value.snapshot?.microphonePermission)
        monitor.onBackground()
        permission = false
        monitor.onForeground()
        assertTrue(monitor.state.value.stale)
        runCurrent()
        assertEquals(2, reads)
        assertEquals(Observation.Known(false), monitor.state.value.snapshot?.microphonePermission)
        assertFalse(monitor.state.value.stale)
        assertEquals(DiagnosticRemedy.OPEN_APP_SETTINGS,
            diagnose(monitor.state.value.snapshot!!).single { it.title == "Microphone" }.remedy)
        monitor.close()
    }

    @Test fun nonCancellableOldReadCannotOverwriteACompletedNewRefresh() = runTest {
        val oldRead = CompletableDeferred<DeviceSnapshot>()
        var reads = 0
        val monitor = DeviceStatusMonitor(this) {
            if (++reads == 1) withContext(NonCancellable) { oldRead.await() } else snapshot(2)
        }
        monitor.onForeground()
        runCurrent()
        monitor.refresh()
        runCurrent()
        assertEquals(snapshot(2), monitor.state.value.snapshot)
        val current = monitor.state.value
        oldRead.complete(snapshot(1))
        runCurrent()
        assertEquals(current, monitor.state.value)
        monitor.close()
    }

    @Test fun cancelledOldRefreshCannotClearTheBusyStateOfItsReplacement() = runTest {
        val oldRead = CompletableDeferred<DeviceSnapshot>()
        val newRead = CompletableDeferred<DeviceSnapshot>()
        var reads = 0
        val monitor = DeviceStatusMonitor(this) {
            if (++reads == 1) oldRead.await() else newRead.await()
        }
        monitor.onForeground()
        runCurrent()
        monitor.refresh()
        runCurrent()
        assertEquals(2, reads)
        assertTrue(monitor.state.value.refreshing)
        assertFalse(monitor.state.value.refreshFailed)
        newRead.complete(snapshot(2))
        runCurrent()
        assertEquals(snapshot(2), monitor.state.value.snapshot)
        assertFalse(monitor.state.value.refreshing)
        monitor.close()
    }

    @Test fun backgroundFencesAnOldNonCancellableReadAcrossResume() = runTest {
        val oldRead = CompletableDeferred<DeviceSnapshot>()
        var reads = 0
        val monitor = DeviceStatusMonitor(this) {
            if (++reads == 1) withContext(NonCancellable) { oldRead.await() } else snapshot(2)
        }
        monitor.onForeground()
        runCurrent()
        monitor.onBackground()
        assertTrue(monitor.state.value.stale)
        assertFalse(monitor.state.value.refreshing)
        monitor.onForeground()
        runCurrent()
        val resumed = monitor.state.value
        oldRead.complete(snapshot(1))
        runCurrent()
        assertEquals(snapshot(2), resumed.snapshot)
        assertEquals(resumed, monitor.state.value)
        monitor.close()
    }

    @Test fun closeFencesALateNonCancellableReadAndAllFutureRefreshRequests() = runTest {
        val lateRead = CompletableDeferred<DeviceSnapshot>()
        var reads = 0
        val monitor = DeviceStatusMonitor(this) {
            reads++
            withContext(NonCancellable) { lateRead.await() }
        }
        monitor.onForeground()
        runCurrent()
        monitor.close()
        val closed = monitor.state.value
        lateRead.complete(snapshot(1))
        runCurrent()
        monitor.onForeground()
        monitor.refresh()
        monitor.close()
        runCurrent()
        assertEquals(1, reads)
        assertEquals(closed, monitor.state.value)
        assertNull(closed.snapshot)
        assertTrue(closed.stale)
        assertFalse(closed.refreshing)
        assertFalse(closed.refreshFailed)
    }

    @Test fun failedRefreshPreservesTheOldSnapshotAsStaleAndCanRecover() = runTest {
        var reads = 0
        val monitor = DeviceStatusMonitor(this) {
            if (++reads == 2) throw IOException("unavailable platform reading")
            snapshot(reads)
        }
        monitor.onForeground()
        runCurrent()
        monitor.refresh()
        assertEquals(snapshot(1), monitor.state.value.snapshot)
        assertTrue(monitor.state.value.stale)
        assertTrue(monitor.state.value.refreshing)
        runCurrent()
        assertEquals(snapshot(1), monitor.state.value.snapshot)
        assertTrue(monitor.state.value.stale)
        assertTrue(monitor.state.value.refreshFailed)
        assertFalse(monitor.state.value.refreshing)
        monitor.refresh()
        assertFalse(monitor.state.value.refreshFailed)
        runCurrent()
        assertEquals(snapshot(3), monitor.state.value.snapshot)
        assertFalse(monitor.state.value.stale)
        assertFalse(monitor.state.value.refreshFailed)
        monitor.close()
    }

    @Test fun collectorCancellationSettlesWithoutReportingARefreshFailure() = runTest {
        var reads = 0
        val monitor = DeviceStatusMonitor(this) {
            if (++reads == 2) throw CancellationException("reading cancelled")
            snapshot(reads)
        }
        monitor.onForeground()
        runCurrent()
        monitor.refresh()
        runCurrent()
        assertEquals(snapshot(1), monitor.state.value.snapshot)
        assertTrue(monitor.state.value.stale)
        assertFalse(monitor.state.value.refreshing)
        assertFalse(monitor.state.value.refreshFailed)
        monitor.close()
    }

    private fun snapshot(sequence: Int) = DeviceSnapshot(
        observedAtElapsedMillis = sequence.toLong(), apiLevel = 36,
        microphoneHardware = Observation.Known(true), microphonePermission = Observation.Known(true),
        availableAppFilesystemBytes = Observation.Known(64L * 1024 * 1024),
        batteryPercent = Observation.Known(80), charging = Observation.Known(false),
        powerSaveMode = Observation.Known(false),
    )
}
