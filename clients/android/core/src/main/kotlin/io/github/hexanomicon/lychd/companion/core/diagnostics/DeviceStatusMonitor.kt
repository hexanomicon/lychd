package io.github.hexanomicon.lychd.companion.core.diagnostics

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlin.coroutines.coroutineContext

data class DeviceStatus(
    val snapshot: DeviceSnapshot? = null,
    val refreshing: Boolean = false,
    val stale: Boolean = true,
    val refreshFailed: Boolean = false,
)

/** Foreground-only sampling on a serialized owner thread, independent of host working offers. */
class DeviceStatusMonitor(
    private val scope: CoroutineScope,
    private val collect: suspend () -> DeviceSnapshot,
) {
    private val mutableState = MutableStateFlow(DeviceStatus())
    val state = mutableState.asStateFlow()
    private var foreground = false
    private var closed = false
    private var generation = Any()
    private var job: Job? = null

    fun onForeground() {
        if (closed) return
        foreground = true
        refresh()
    }

    fun refresh() {
        if (!foreground || closed) return
        generation = Any()
        val origin = generation
        job?.cancel()
        mutableState.value = mutableState.value.copy(refreshing = true, stale = true, refreshFailed = false)
        job = scope.launch {
            try {
                val snapshot = collect()
                coroutineContext.ensureActive()
                if (foreground && !closed && origin === generation) mutableState.value = DeviceStatus(snapshot, stale = false)
            } catch (cancelled: CancellationException) {
                if (foreground && !closed && origin === generation) mutableState.value =
                    mutableState.value.copy(refreshing = false, stale = true)
                throw cancelled
            } catch (_: Exception) {
                if (foreground && !closed && origin === generation) mutableState.value =
                    mutableState.value.copy(refreshing = false, stale = true, refreshFailed = true)
            }
        }
    }

    fun onBackground() {
        foreground = false
        generation = Any()
        job?.cancel()
        job = null
        mutableState.value = mutableState.value.copy(refreshing = false, stale = true)
    }

    fun close() {
        closed = true
        onBackground()
    }
}
