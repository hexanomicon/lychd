package io.github.hexanomicon.lychd.companion.core.diagnostics

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class DeviceDiagnosticsTest {
    @Test fun grantedPermissionReportsAnObservationWithoutQualifyingCapture() {
        val check = diagnose(snapshot()).check("Microphone")
        assertTrue(check.observation.contains("permission granted"))
        assertTrue(check.nextStep.contains("not been tested"))
        assertTrue(check.nextStep.contains("Mic access"))
        assertFalse(Regex("\\b(ready|healthy|qualified|verified)\\b", RegexOption.IGNORE_CASE)
            .containsMatchIn(check.observation + " " + check.nextStep))
        assertNull(check.remedy)
    }

    @Test fun absentHardwareCannotBeRemediedByChangingAppPermissions() {
        for (permission in listOf(Observation.Known(true), Observation.Known(false), Observation.Unknown)) {
            val check = diagnose(snapshot().copy(
                microphoneHardware = Observation.Known(false), microphonePermission = permission,
            )).check("Microphone")
            assertTrue(check.needsAttention)
            assertTrue(check.observation.contains("no microphone hardware"))
            assertTrue(check.nextStep.contains("words editor"))
            assertNull(check.remedy)
        }
    }

    @Test fun deniedPermissionOffersAppSettingsOnlyWhenHardwareIsKnownPresent() {
        val denied = diagnose(snapshot().copy(microphonePermission = Observation.Known(false)))
            .check("Microphone")
        assertTrue(denied.needsAttention)
        assertEquals(DiagnosticRemedy.OPEN_APP_SETTINGS, denied.remedy)
        val unknownHardware = diagnose(snapshot().copy(
            microphoneHardware = Observation.Unknown, microphonePermission = Observation.Known(false),
        )).check("Microphone")
        assertNull(unknownHardware.remedy)
        assertNotEquals(denied.observation, unknownHardware.observation)
    }

    @Test fun missingPermissionDoesNotBecomeADenialOrAnInvitationToSettings() {
        val unknown = diagnose(snapshot().copy(microphonePermission = Observation.Unknown))
            .check("Microphone")
        assertTrue(unknown.needsAttention)
        assertTrue(unknown.observation.contains("could not be checked"))
        assertNull(unknown.remedy)
        assertNotEquals(diagnose(snapshot().copy(microphonePermission = Observation.Known(false)))
            .check("Microphone").observation, unknown.observation)
    }

    @Test fun invalidBatteryExtrasStayUnknownWhileValidZeroIsKnown() {
        for ((level, scale) in listOf(-1 to 100, 0 to 0, 20 to -1, 101 to 100,
            Int.MIN_VALUE to Int.MAX_VALUE, Int.MAX_VALUE to 100)) {
            assertEquals("level=$level scale=$scale", Observation.Unknown, batteryPercent(level, scale))
        }
        assertEquals(Observation.Known(0), batteryPercent(0, 100))
        assertEquals(Observation.Known(50), batteryPercent(1, 2))
        assertEquals(Observation.Known(100), batteryPercent(Int.MAX_VALUE, Int.MAX_VALUE))
        assertEquals(Observation.Known(99), batteryPercent(Int.MAX_VALUE - 1, Int.MAX_VALUE))
    }

    @Test fun missingOrNegativeStorageIsUnknownAndNeverShownAsZeroFreeSpace() {
        val zero = diagnose(snapshot().copy(availableAppFilesystemBytes = Observation.Known(0L)))
            .check("App-data storage")
        assertTrue(zero.observation.contains("0 MiB"))
        for (reading in listOf(Observation.Unknown, Observation.Known(-1L), Observation.Known(Long.MIN_VALUE))) {
            val check = diagnose(snapshot().copy(availableAppFilesystemBytes = reading))
                .check("App-data storage")
            assertTrue(check.needsAttention)
            assertTrue(check.observation.contains("could not be checked"))
            assertFalse(check.observation.contains("0 MiB"))
            assertNotEquals(zero.nextStep, check.nextStep)
        }
    }

    @Test fun storageAdviceChangesAtExactly32MiB() {
        val threshold = 32L * 1024 * 1024
        assertTrue(diagnose(snapshot().copy(availableAppFilesystemBytes = Observation.Known(threshold - 1)))
            .check("App-data storage").needsAttention)
        for (bytes in listOf(threshold, threshold + 1, Long.MAX_VALUE)) {
            val check = diagnose(snapshot().copy(availableAppFilesystemBytes = Observation.Known(bytes)))
                .check("App-data storage")
            assertFalse(check.needsAttention)
            assertTrue(check.nextStep.contains("guarantee"))
        }
    }

    @Test fun lowBatteryAdviceIncludes15PercentAndRecognizesCharging() {
        for (percent in listOf(0, 14, 15)) {
            for (charging in listOf(Observation.Known(false), Observation.Unknown)) {
                val check = diagnose(snapshot().copy(batteryPercent = Observation.Known(percent), charging = charging))
                    .check("Battery")
                assertTrue(check.needsAttention)
                assertTrue(check.nextStep.contains("Connect power"))
            }
            val charging = diagnose(snapshot().copy(
                batteryPercent = Observation.Known(percent), charging = Observation.Known(true),
            )).check("Battery")
            assertFalse(charging.needsAttention)
            assertTrue(charging.observation.contains("charging or full"))
            assertFalse(charging.nextStep.contains("Connect power"))
        }
        assertFalse(diagnose(snapshot().copy(batteryPercent = Observation.Known(16), charging = Observation.Known(false)))
            .check("Battery").needsAttention)
    }

    @Test fun unknownBatteryChargingAndPowerSavingStayDistinctFromZeroAndDisabled() {
        for (percent in listOf(Observation.Unknown, Observation.Known(-1), Observation.Known(101))) {
            val check = diagnose(snapshot().copy(batteryPercent = percent, charging = Observation.Unknown))
                .check("Battery")
            assertTrue(check.needsAttention)
            assertTrue(check.observation.contains("Battery level unknown"))
            assertTrue(check.observation.contains("charging state unknown"))
            assertFalse(check.observation.contains("0%"))
            assertFalse(check.observation.contains("not charging"))
        }
        val unknown = diagnose(snapshot().copy(powerSaveMode = Observation.Unknown)).check("Power saving")
        val disabled = diagnose(snapshot()).check("Power saving")
        val enabled = diagnose(snapshot().copy(powerSaveMode = Observation.Known(true))).check("Power saving")
        assertTrue(unknown.needsAttention)
        assertTrue(unknown.observation.contains("could not be checked"))
        assertFalse(disabled.needsAttention)
        assertTrue(enabled.needsAttention)
        assertNotEquals(disabled.observation, unknown.observation)
        assertNotEquals(enabled.observation, unknown.observation)
    }

    private fun List<DiagnosticCheck>.check(title: String) = single { it.title == title }

    private fun snapshot() = DeviceSnapshot(
        observedAtElapsedMillis = 10, apiLevel = 36,
        microphoneHardware = Observation.Known(true), microphonePermission = Observation.Known(true),
        availableAppFilesystemBytes = Observation.Known(64L * 1024 * 1024),
        batteryPercent = Observation.Known(80), charging = Observation.Known(false),
        powerSaveMode = Observation.Known(false),
    )
}
