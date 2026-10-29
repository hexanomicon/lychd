package io.github.hexanomicon.lychd.companion

import android.app.Application
import android.os.SystemClock
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import io.github.hexanomicon.lychd.companion.audio.ForegroundRecorder
import io.github.hexanomicon.lychd.companion.audio.ReplyPlayer
import io.github.hexanomicon.lychd.companion.core.BridgeStore
import io.github.hexanomicon.lychd.companion.core.createFixtureBridgeTransport
import io.github.hexanomicon.lychd.companion.core.diagnostics.DeviceStatusMonitor
import io.github.hexanomicon.lychd.companion.core.presentation.PresentationGate
import io.github.hexanomicon.lychd.companion.core.presentation.PresentationPolicy
import io.github.hexanomicon.lychd.companion.diagnostics.AndroidDeviceStatus

/** Android assembly and lifecycle bridge for the independently tested interaction controller. */
class CompanionViewModel(application: Application) : AndroidViewModel(application) {
    private val deviceStatus = DeviceStatusMonitor(viewModelScope, AndroidDeviceStatus(application)::collect)
    private val controller = CompanionController(
        store = if (BuildConfig.DEBUG) BridgeStore(createFixtureBridgeTransport()) else null,
        scope = viewModelScope,
        recorderFactory = { ForegroundRecorder(application) },
        playerFactory = { ReplyPlayer(application) },
        elapsedRealtime = SystemClock::elapsedRealtime,
        gate = PresentationGate(if (BuildConfig.DEBUG) PresentationPolicy.developmentFixture() else PresentationPolicy.unavailable()),
    )
    val presentationState = controller.presentationState
    val bridgeState = controller.bridgeState
    val voiceState = controller.voiceState
    val wordsReviewed = controller.wordsReviewed
    val deviceStatusState = deviceStatus.state
    fun refreshDeviceStatus() = deviceStatus.refresh()
    fun editDraft(text: String, generation: Long) = controller.editDraft(text, generation)
    fun reviewWords(reviewed: Boolean, generation: Long) = controller.reviewWords(reviewed, generation)
    fun send(generation: Long) = controller.send(generation)
    fun refresh(generation: Long) = controller.refresh(generation)
    fun newConversation(generation: Long) = controller.newConversation(generation)
    fun replacePresentationPolicy(policy: PresentationPolicy) = controller.replacePresentationPolicy(policy)
    fun onForeground() {
        controller.onForeground()
        deviceStatus.onForeground()
    }
    fun onBackground() {
        deviceStatus.onBackground()
        controller.onBackground()
    }
    fun microphonePermissionDenied(generation: Long) = controller.microphonePermissionDenied(generation)
    fun startRecording(generation: Long) = controller.startRecording(generation)
    fun stopRecording() = controller.stopRecording()
    fun replayRecording(generation: Long) = controller.replayRecording(generation)
    fun stopReplay() = controller.stopReplay()
    fun discardRecording() = controller.discardRecording()
    fun releaseAudioResources() = controller.releaseAudioResources()
    override fun onCleared() {
        deviceStatus.close()
        controller.close()
        super.onCleared()
    }
}
