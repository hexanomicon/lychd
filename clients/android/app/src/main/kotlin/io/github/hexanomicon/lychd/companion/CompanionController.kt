package io.github.hexanomicon.lychd.companion

import io.github.hexanomicon.lychd.companion.audio.AudioCleanup
import io.github.hexanomicon.lychd.companion.audio.LocalPlayer
import io.github.hexanomicon.lychd.companion.audio.LocalRecorder
import io.github.hexanomicon.lychd.companion.audio.RecordedAudio
import io.github.hexanomicon.lychd.companion.audio.ReplayEvent
import io.github.hexanomicon.lychd.companion.core.BridgeState
import io.github.hexanomicon.lychd.companion.core.BridgeStore
import io.github.hexanomicon.lychd.companion.core.presentation.CompanionAction
import io.github.hexanomicon.lychd.companion.core.presentation.OfferDecision
import io.github.hexanomicon.lychd.companion.core.presentation.PolicySource
import io.github.hexanomicon.lychd.companion.core.presentation.PresentationGate
import io.github.hexanomicon.lychd.companion.core.presentation.PresentationPolicy
import io.github.hexanomicon.lychd.companion.ui.RecordingDiscards
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

enum class CapturePhase { IDLE, STARTING, RECORDING, STOPPING }

data class VoiceUiState(
    val phase: CapturePhase = CapturePhase.IDLE,
    val elapsedMillis: Long = 0,
    val recording: RecordedAudio? = null,
    val replayRequested: Boolean = false,
    val replayPlaying: Boolean = false,
    val cleanupRequired: Boolean = false,
    val error: String? = null,
    val notice: String? = null,
)

/**
 * Transient mechanics; local offers neither identify a person nor authorize host work.
 * Entry points, the supplied scope and player callbacks share one serialized owner thread
 * (Android's main thread in the application).
 */
internal class CompanionController(
    private val store: BridgeStore?,
    private val scope: CoroutineScope,
    private val recorderFactory: () -> LocalRecorder,
    private val playerFactory: () -> LocalPlayer,
    private val elapsedRealtime: () -> Long,
    private val gate: PresentationGate = PresentationGate(),
) {
    val presentationState = gate.state
    val bridgeState: StateFlow<BridgeState> = store?.state ?: MutableStateFlow(BridgeState()).asStateFlow()
    private val mutableVoice = MutableStateFlow(VoiceUiState())
    val voiceState = mutableVoice.asStateFlow()
    private val mutableReviewed = MutableStateFlow(false)
    val wordsReviewed = mutableReviewed.asStateFlow()
    private var foreground = false
    private var closed = false
    private var lifetimeGeneration = 0L
    private var audioGeneration = 0L
    private var replayGeneration = 0L
    // Approval belongs to one review decision, even when later edits restore identical words.
    private var reviewToken = Any()
    private var recorder: LocalRecorder? = if (gate.state.value.policy.source == PolicySource.DEVELOPMENT_FIXTURE) recorderFactory() else null
    private var player: LocalPlayer? = null
    // Adapter destruction does not discharge its byte custody or an overflow restart latch.
    private var recorderCleanupDebt = AudioCleanup(clean = true)
    private var captureJob: Job? = null
    private var timerJob: Job? = null
    private val recordingDiscards = RecordingDiscards()

    private data class Origin(val presentation: Long, val lifetime: Long)
    private fun origin(expectedPresentationGeneration: Long = gate.state.value.generation) =
        Origin(expectedPresentationGeneration, lifetimeGeneration)
    private fun offered(action: CompanionAction, origin: Origin = origin()): Boolean =
        !closed && foreground && origin.lifetime == lifetimeGeneration &&
            gate.state.value.decision(action, origin.presentation) == OfferDecision.OFFERED

    fun editDraft(text: String, expectedPresentationGeneration: Long = gate.state.value.generation) {
        if (!offered(CompanionAction.EDIT_WORDS, origin(expectedPresentationGeneration))) return
        invalidateReview()
        store?.editDraft(text)
    }

    fun reviewWords(reviewed: Boolean, expectedPresentationGeneration: Long = gate.state.value.generation) {
        if (!offered(CompanionAction.REVIEW_WORDS, origin(expectedPresentationGeneration))) return
        invalidateReview()
        mutableReviewed.value = reviewed && bridgeState.value.draft.isNotBlank()
    }

    private fun invalidateReview() {
        reviewToken = Any()
        mutableReviewed.value = false
    }

    fun send(expectedPresentationGeneration: Long = gate.state.value.generation) {
        val state = bridgeState.value
        val origin = origin(expectedPresentationGeneration)
        if (!offered(CompanionAction.SEND_WORDS, origin) || !mutableReviewed.value || state.busy ||
            state.sessionId == null || state.hasUncertainSubmission || mutableVoice.value.phase != CapturePhase.IDLE
        ) return
        val approval = reviewToken
        mutableReviewed.value = false
        scope.launch {
            if (offered(CompanionAction.SEND_WORDS, origin) && reviewToken === approval &&
                bridgeState.value.draft == state.draft &&
                bridgeState.value.sessionId == state.sessionId && mutableVoice.value.phase == CapturePhase.IDLE
            ) store?.send()
        }
    }

    fun refresh(expectedPresentationGeneration: Long = gate.state.value.generation) {
        val sessionId = bridgeState.value.sessionId
        val action = if (sessionId == null) CompanionAction.OPEN_CONVERSATION else CompanionAction.REFRESH_CONVERSATION
        val origin = origin(expectedPresentationGeneration)
        if (!offered(action, origin) || bridgeState.value.busy) return
        scope.launch {
            if (!offered(action, origin) || bridgeState.value.sessionId != sessionId) return@launch
            if (sessionId == null) store?.connect() else store?.refresh()
        }
    }

    fun newConversation(expectedPresentationGeneration: Long = gate.state.value.generation) {
        val origin = origin(expectedPresentationGeneration)
        if (!offered(CompanionAction.OPEN_CONVERSATION, origin) || bridgeState.value.busy) return
        cancelLocalAudio()
        invalidateReview()
        scope.launch { if (offered(CompanionAction.OPEN_CONVERSATION, origin)) store?.newSession() }
    }

    fun replacePresentationPolicy(policy: PresentationPolicy) {
        gate.replace(policy)
        lifetimeGeneration += 1
        store?.clearProjection()
        invalidateReview()
        cancelLocalAudio()
        if (foreground) openIfOffered()
    }

    fun onForeground() {
        if (closed) return
        foreground = true
        if (mutableVoice.value.cleanupRequired) cancelLocalAudio("Local audio discarded.")
        openIfOffered()
    }

    private fun openIfOffered() {
        val origin = origin()
        if (!offered(CompanionAction.OPEN_CONVERSATION, origin) || bridgeState.value.sessionId != null) return
        scope.launch { if (offered(CompanionAction.OPEN_CONVERSATION, origin)) store?.connect() }
    }

    fun onBackground() {
        foreground = false
        lifetimeGeneration += 1
        store?.invalidate()
        val hadAudio = mutableVoice.value.phase != CapturePhase.IDLE || mutableVoice.value.recording != null
        cancelLocalAudio(if (hadAudio) "Audio stopped when the app left the foreground. Temporary files are checked before another recording." else null)
    }

    fun microphonePermissionDenied(expectedPresentationGeneration: Long = gate.state.value.generation) {
        if (!offered(CompanionAction.START_RECORDING, origin(expectedPresentationGeneration))) return
        mutableVoice.value = mutableVoice.value.copy(
            error = "Microphone access was denied. You can still enter words manually; Android app settings can restore access.",
            notice = null,
        )
    }

    fun startRecording(expectedPresentationGeneration: Long = gate.state.value.generation) {
        val origin = origin(expectedPresentationGeneration)
        if (!offered(CompanionAction.START_RECORDING, origin) || mutableVoice.value.phase != CapturePhase.IDLE) return
        if (!cancelLocalAudio()) return
        val generation = audioGeneration
        val activeRecorder = recorder ?: recorderFactory().also { recorder = it }
        mutableVoice.value = VoiceUiState(phase = CapturePhase.STARTING)
        captureJob = scope.launch {
            try {
                if (!audioIsCurrent(generation, origin) || !offered(CompanionAction.START_RECORDING, origin)) return@launch
                activeRecorder.start()
                if (!audioIsCurrent(generation, origin)) {
                    return@launch
                }
                mutableVoice.value = mutableVoice.value.copy(phase = CapturePhase.RECORDING)
                val startedAt = elapsedRealtime()
                timerJob = scope.launch {
                    while (audioIsCurrent(generation, origin) && mutableVoice.value.phase == CapturePhase.RECORDING) {
                        mutableVoice.value = mutableVoice.value.copy(elapsedMillis = (elapsedRealtime() - startedAt).coerceIn(0, CAPTURE_LIMIT_MILLIS))
                        delay(100)
                    }
                }
                val completed = activeRecorder.awaitRecording()
                if (!audioIsCurrent(generation, origin)) {
                    if (completed != null && !recordingDiscards.discard(completed.file)) cancelLocalAudio()
                    return@launch
                }
                timerJob?.cancel()
                timerJob = null
                rememberRecorderCleanup(activeRecorder.retryCleanup())
                if (!recorderCleanupDebt.clean) {
                    if (completed != null) recordingDiscards.discard(completed.file)
                    cancelLocalAudio()
                    return@launch
                }
                mutableVoice.value = if (completed == null) VoiceUiState(error = "No completed recording is available. Enter words manually or record again.")
                else VoiceUiState(recording = completed, elapsedMillis = completed.durationMillis)
            } catch (cancelled: CancellationException) {
                // A cancelled IO start can finish disposing its partial file after the stop call.
                val cleanup = activeRecorder.retryCleanup()
                if (!cleanup.clean) {
                    rememberRecorderCleanup(cleanup)
                    cancelLocalAudio()
                }
                throw cancelled
            } catch (_: Exception) {
                val current = audioIsCurrent(generation, origin)
                val starting = mutableVoice.value.phase == CapturePhase.STARTING
                // Cancelled IO can still throw a storage error after its owner's generation ends.
                val cleanup = activeRecorder.retryCleanup()
                if (!cleanup.clean) {
                    rememberRecorderCleanup(cleanup)
                }
                if (current || !cleanup.clean) {
                    val clean = cancelLocalAudio()
                    if (current && clean) mutableVoice.value = VoiceUiState(error = if (starting) "Recording could not start. Check microphone access and local storage, then try again."
                        else "Recording was interrupted. Check microphone access, then try again.")
                }
            }
        }
    }

    fun stopRecording() {
        when (mutableVoice.value.phase) {
            CapturePhase.STARTING -> cancelLocalAudio("Recording cancelled.")
            CapturePhase.RECORDING -> {
                timerJob?.cancel()
                timerJob = null
                mutableVoice.value = mutableVoice.value.copy(phase = CapturePhase.STOPPING)
                recorder?.requestStop()
            }
            else -> Unit
        }
    }

    fun replayRecording(expectedPresentationGeneration: Long = gate.state.value.generation) {
        val origin = origin(expectedPresentationGeneration)
        val recording = mutableVoice.value.recording ?: return
        if (!offered(CompanionAction.REPLAY_RECORDING, origin) || mutableVoice.value.phase != CapturePhase.IDLE) return
        val generation = audioGeneration
        val replay = ++replayGeneration
        try {
            val activePlayer = player ?: playerFactory().also { player = it }
            mutableVoice.value = mutableVoice.value.copy(replayRequested = true, replayPlaying = false, error = null)
            activePlayer.play(recording.file) { event ->
                if (audioIsCurrent(generation, origin) && replay == replayGeneration) {
                    mutableVoice.value = when (event) {
                        ReplayEvent.PLAYING -> mutableVoice.value.copy(replayPlaying = true)
                        ReplayEvent.NOT_PLAYING -> mutableVoice.value.copy(replayPlaying = false)
                        ReplayEvent.ENDED -> mutableVoice.value.copy(replayRequested = false, replayPlaying = false)
                        ReplayEvent.FAILED -> mutableVoice.value.copy(replayRequested = false, replayPlaying = false, error = "Local replay failed. Try replay again or discard the recording.")
                    }
                }
            }
        } catch (_: Exception) {
            player?.stop()
            mutableVoice.value = mutableVoice.value.copy(replayRequested = false, replayPlaying = false, error = "Local replay could not start.")
        }
    }

    fun stopReplay() {
        replayGeneration += 1
        player?.stop()
        mutableVoice.value = mutableVoice.value.copy(replayRequested = false, replayPlaying = false)
    }

    fun discardRecording() { cancelLocalAudio("Local recording discarded.") }

    fun releaseAudioResources() {
        cancelLocalAudio()
        recorder?.close()
        player?.close()
        recorder = null
        player = null
    }

    private fun audioIsCurrent(generation: Long, origin: Origin): Boolean =
        !closed && foreground && generation == audioGeneration && origin.lifetime == lifetimeGeneration &&
            origin.presentation == gate.state.value.generation

    private fun cancelLocalAudio(notice: String? = null): Boolean {
        audioGeneration += 1
        captureJob?.cancel()
        timerJob?.cancel()
        captureJob = null
        timerJob = null
        if (recorder == null && !recorderCleanupDebt.clean && !closed) recorder = recorderFactory()
        recorder?.let { rememberRecorderCleanup(it.cancel()) }
        player?.stop()
        val recording = mutableVoice.value.recording
        val discarded = if (recording == null) recordingDiscards.retry() else recordingDiscards.discard(recording.file)
        val clean = recorderCleanupDebt.clean && discarded
        mutableVoice.value = if (clean) VoiceUiState(notice = notice)
        else VoiceUiState(cleanupRequired = true, error = if (recorderCleanupDebt.restartRequired || recordingDiscards.restartRequired)
            "Force-stop and reopen the app to retry local audio cleanup. Recording is blocked."
            else "Local audio could not be discarded. Retry discard before recording again.")
        return clean
    }

    private fun rememberRecorderCleanup(result: AudioCleanup) {
        val restart = recorderCleanupDebt.restartRequired || result.restartRequired
        recorderCleanupDebt = AudioCleanup(clean = result.clean && !restart, restartRequired = restart)
    }

    fun close() {
        foreground = false
        lifetimeGeneration += 1
        closed = true
        releaseAudioResources()
        store?.close()
    }

    private companion object { const val CAPTURE_LIMIT_MILLIS = 15_000L }
}
