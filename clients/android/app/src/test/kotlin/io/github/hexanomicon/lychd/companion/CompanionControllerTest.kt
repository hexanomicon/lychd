package io.github.hexanomicon.lychd.companion

import io.github.hexanomicon.lychd.companion.audio.AudioCleanup
import io.github.hexanomicon.lychd.companion.audio.LocalPlayer
import io.github.hexanomicon.lychd.companion.audio.LocalRecorder
import io.github.hexanomicon.lychd.companion.audio.RecordedAudio
import io.github.hexanomicon.lychd.companion.audio.ReplayEvent
import io.github.hexanomicon.lychd.companion.core.BridgeSession
import io.github.hexanomicon.lychd.companion.core.BridgeStore
import io.github.hexanomicon.lychd.companion.core.BridgeTransport
import io.github.hexanomicon.lychd.companion.core.SubmittedTurn
import io.github.hexanomicon.lychd.companion.core.presentation.CompanionAction
import io.github.hexanomicon.lychd.companion.core.presentation.CompanionScreenId
import io.github.hexanomicon.lychd.companion.core.presentation.PresentationGate
import io.github.hexanomicon.lychd.companion.core.presentation.PresentationPolicy
import java.io.File
import java.io.IOException
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.withContext
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class CompanionControllerTest {
    @Test fun unavailablePolicyDeniesAutomaticOpenAndDirectActions() = runTest {
        val setup = setup(PresentationPolicy.unavailable())
        setup.controller.onForeground()
        setup.controller.refresh()
        setup.controller.newConversation()
        setup.controller.editDraft("private")
        setup.controller.reviewWords(true)
        setup.controller.send()
        setup.controller.startRecording()
        setup.controller.replayRecording()
        runCurrent()
        assertEquals(0, setup.transport.opens)
        assertEquals(0, setup.transport.submits)
        assertEquals(0, setup.recorder.starts)
        assertEquals("", setup.controller.bridgeState.value.draft)
        setup.controller.close()
    }

    @Test fun readOnlyOfferCannotOpenThroughInitOrRefreshFallback() = runTest {
        val setup = setup(PresentationPolicy.developmentFixture(
            screens = setOf(CompanionScreenId.CONVERSATION),
            actions = setOf(CompanionAction.REFRESH_CONVERSATION),
        ))
        setup.controller.onForeground()
        setup.controller.refresh()
        setup.controller.newConversation()
        setup.controller.editDraft("private")
        setup.controller.startRecording()
        runCurrent()
        assertEquals(0, setup.transport.opens)
        assertEquals(0, setup.transport.reads)
        assertEquals(0, setup.recorder.starts)
        setup.controller.close()
    }

    @Test fun missingConversationSurfaceDeniesOpenDespiteAction() = runTest {
        val setup = setup(PresentationPolicy.developmentFixture(
            screens = setOf(CompanionScreenId.WORDS),
            actions = CompanionAction.entries.toSet(),
        ))
        setup.controller.onForeground()
        setup.controller.refresh()
        setup.controller.newConversation()
        runCurrent()
        assertEquals(0, setup.transport.opens)
        setup.controller.close()
    }

    @Test fun queuedOpenAndCaptureCannotStartAfterBackground() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        setup.controller.startRecording()
        setup.controller.onBackground()
        runCurrent()
        assertEquals(0, setup.transport.opens)
        assertEquals(0, setup.recorder.starts)
        assertEquals(CapturePhase.IDLE, setup.controller.voiceState.value.phase)
        setup.controller.close()
    }

    @Test fun queuedSendCannotRunAfterBackgroundOrReplacement() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        runCurrent()
        setup.controller.editDraft("reviewed")
        setup.controller.reviewWords(true)
        setup.controller.send()
        setup.controller.onBackground()
        runCurrent()
        assertEquals(0, setup.transport.submits)
        assertEquals("reviewed", setup.controller.bridgeState.value.draft)
        setup.controller.onForeground()
        setup.controller.reviewWords(true)
        setup.controller.send()
        setup.controller.replacePresentationPolicy(PresentationPolicy.unavailable())
        runCurrent()
        assertEquals(0, setup.transport.submits)
        assertNull(setup.controller.bridgeState.value.sessionId)
        assertEquals("", setup.controller.bridgeState.value.draft)
        assertFalse(setup.controller.wordsReviewed.value)
        setup.controller.close()
    }

    @Test fun editingQueuedReviewedWordsPreventsTheirSend() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        runCurrent()
        setup.controller.editDraft("reviewed")
        setup.controller.reviewWords(true)
        setup.controller.send()
        setup.controller.editDraft("changed after review")
        runCurrent()
        assertEquals(0, setup.transport.submits)
        setup.controller.close()
    }

    @Test fun returningToTheReviewedWordsDoesNotReviveAQueuedSend() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        runCurrent()
        setup.controller.editDraft("A")
        setup.controller.reviewWords(true)
        setup.controller.send()
        setup.controller.editDraft("B")
        setup.controller.editDraft("A")
        runCurrent()
        assertEquals(0, setup.transport.submits)
        assertEquals("A", setup.controller.bridgeState.value.draft)
        assertFalse(setup.controller.wordsReviewed.value)
        setup.controller.close()
    }

    @Test fun evenAnIdenticalDraftEditInvalidatesAQueuedSend() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        runCurrent()
        setup.controller.editDraft("A")
        setup.controller.reviewWords(true)
        setup.controller.send()
        setup.controller.editDraft("A")
        runCurrent()
        assertEquals(0, setup.transport.submits)
        assertFalse(setup.controller.wordsReviewed.value)
        setup.controller.close()
    }

    @Test fun explicitReviewRevocationCancelsAQueuedSend() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        runCurrent()
        setup.controller.editDraft("A")
        setup.controller.reviewWords(true)
        setup.controller.send()
        setup.controller.reviewWords(false)
        runCurrent()
        assertEquals(0, setup.transport.submits)
        assertFalse(setup.controller.wordsReviewed.value)
        setup.controller.close()
    }

    @Test fun newReviewAfterReturningToTheWordsNeedsItsOwnSend() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        runCurrent()
        setup.controller.editDraft("A")
        setup.controller.reviewWords(true)
        setup.controller.send()
        setup.controller.editDraft("B")
        setup.controller.editDraft("A")
        setup.controller.reviewWords(true)
        runCurrent()
        assertEquals(0, setup.transport.submits)
        assertTrue(setup.controller.wordsReviewed.value)
        setup.controller.send()
        runCurrent()
        assertEquals(1, setup.transport.submits)
        setup.controller.close()
    }

    @Test fun revokingAndReviewingAgainNeedsANewSend() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        runCurrent()
        setup.controller.editDraft("A")
        setup.controller.reviewWords(true)
        setup.controller.send()
        setup.controller.reviewWords(false)
        setup.controller.reviewWords(true)
        runCurrent()
        assertEquals(0, setup.transport.submits)
        assertTrue(setup.controller.wordsReviewed.value)
        setup.controller.send()
        setup.controller.send()
        runCurrent()
        assertEquals(1, setup.transport.submits)
        setup.controller.close()
    }

    @Test fun unchangedReviewedWordsCanBeSentOnce() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        runCurrent()
        setup.controller.editDraft("A")
        setup.controller.reviewWords(true)
        setup.controller.send()
        setup.controller.send()
        runCurrent()
        assertEquals(1, setup.transport.submits)
        assertFalse(setup.controller.wordsReviewed.value)
        setup.controller.close()
    }

    @Test fun staleRenderActionsCannotChangeTheReplacementContext() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        runCurrent()
        val oldGeneration = setup.controller.presentationState.value.generation
        setup.controller.replacePresentationPolicy(PresentationPolicy.developmentFixture())
        runCurrent()
        setup.controller.editDraft("current")
        setup.controller.reviewWords(true)
        val bridge = setup.controller.bridgeState.value
        val voice = setup.controller.voiceState.value
        setup.controller.editDraft("stale", oldGeneration)
        setup.controller.reviewWords(false, oldGeneration)
        setup.controller.send(oldGeneration)
        setup.controller.refresh(oldGeneration)
        setup.controller.newConversation(oldGeneration)
        setup.controller.startRecording(oldGeneration)
        setup.controller.microphonePermissionDenied(oldGeneration)
        runCurrent()
        assertEquals(bridge, setup.controller.bridgeState.value)
        assertEquals(voice, setup.controller.voiceState.value)
        assertTrue(setup.controller.wordsReviewed.value)
        assertEquals(2, setup.transport.opens)
        assertEquals(0, setup.transport.reads)
        assertEquals(0, setup.transport.submits)
        assertEquals(0, setup.recorder.starts)
        setup.controller.close()
    }

    @Test fun staleRenderCannotReplayOrDiscardACurrentRecording() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        runCurrent()
        val oldGeneration = setup.controller.presentationState.value.generation
        setup.controller.replacePresentationPolicy(PresentationPolicy.developmentFixture())
        setup.controller.startRecording(setup.controller.presentationState.value.generation)
        runCurrent()
        setup.recorder.result.complete(RecordedAudio(absentRecording(), 500, 16044))
        runCurrent()
        val voice = setup.controller.voiceState.value
        setup.controller.replayRecording(oldGeneration)
        setup.controller.startRecording(oldGeneration)
        setup.controller.microphonePermissionDenied(oldGeneration)
        assertEquals(voice, setup.controller.voiceState.value)
        assertEquals(0, setup.player.plays)
        assertEquals(1, setup.recorder.starts)
        setup.controller.replayRecording(setup.controller.presentationState.value.generation)
        assertEquals(1, setup.player.plays)
        setup.controller.close()
    }

    @Test fun earlyMicrophoneFailureImmediatelyLeavesRecordingAndShowsError() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        setup.controller.startRecording()
        runCurrent()
        assertEquals(CapturePhase.RECORDING, setup.controller.voiceState.value.phase)
        setup.recorder.result.completeExceptionally(IOException("private device diagnostic"))
        runCurrent()
        assertEquals(CapturePhase.IDLE, setup.controller.voiceState.value.phase)
        assertNotNull(setup.controller.voiceState.value.error)
        assertFalse(setup.controller.voiceState.value.error!!.contains("private"))
        setup.controller.close()
    }

    @Test fun recoveredCleanupDoesNotHideTheCurrentRecordingFailure() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        setup.controller.startRecording()
        runCurrent()
        setup.recorder.cleanupResults.addAll(listOf(AudioCleanup(false), AudioCleanup(true)))
        setup.recorder.result.completeExceptionally(IOException("private device diagnostic"))
        runCurrent()
        assertEquals(CapturePhase.IDLE, setup.controller.voiceState.value.phase)
        assertFalse(setup.controller.voiceState.value.cleanupRequired)
        assertNotNull(setup.controller.voiceState.value.error)
        assertTrue(setup.controller.voiceState.value.error!!.contains("interrupted"))
        assertFalse(setup.controller.voiceState.value.error!!.contains("private"))
        assertTrue(setup.recorder.cleanupResults.isEmpty())
        setup.controller.close()
    }

    @Test fun automaticCaptureCompletionPublishesRecordingWithoutTimerOrUserStop() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        setup.controller.startRecording()
        runCurrent()
        val file = absentRecording()
        setup.recorder.result.complete(RecordedAudio(file, 500, 16044))
        runCurrent()
        assertEquals(CapturePhase.IDLE, setup.controller.voiceState.value.phase)
        assertEquals(file, setup.controller.voiceState.value.recording!!.file)
        setup.controller.close()
    }

    @Test fun stopRequestsDeviceStopAndCompletionSettlesFinishing() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        setup.controller.startRecording()
        runCurrent()
        setup.controller.stopRecording()
        assertEquals(1, setup.recorder.stops)
        assertEquals(CapturePhase.STOPPING, setup.controller.voiceState.value.phase)
        setup.recorder.result.complete(null)
        runCurrent()
        assertEquals(CapturePhase.IDLE, setup.controller.voiceState.value.phase)
        setup.controller.close()
    }

    @Test fun emptyCaptureWithFailedPartialDeletionRemainsBlocked() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        setup.controller.startRecording()
        runCurrent()
        setup.recorder.cleanup = AudioCleanup(false)
        setup.recorder.result.complete(null)
        runCurrent()
        assertTrue(setup.controller.voiceState.value.cleanupRequired)
        assertNull(setup.controller.voiceState.value.notice)
        setup.controller.close()
    }

    @Test fun replayOfferIsCheckedEvenWhenARecordingAlreadyExists() = runTest {
        val setup = setup(PresentationPolicy.developmentFixture(actions = CompanionAction.entries.toSet() - CompanionAction.REPLAY_RECORDING))
        setup.controller.onForeground()
        setup.controller.startRecording()
        runCurrent()
        setup.recorder.result.complete(RecordedAudio(absentRecording(), 500, 16044))
        runCurrent()
        setup.controller.replayRecording()
        assertEquals(0, setup.player.plays)
        assertFalse(setup.controller.voiceState.value.replayRequested)
        setup.controller.close()
    }

    @Test fun partialCleanupFailureBlocksCaptureAndSafetyRetryWorksAfterAccessLoss() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        setup.recorder.cleanup = AudioCleanup(false)
        setup.controller.discardRecording()
        assertTrue(setup.controller.voiceState.value.cleanupRequired)
        assertNull(setup.controller.voiceState.value.notice)
        setup.controller.startRecording()
        runCurrent()
        assertEquals(0, setup.recorder.starts)
        setup.controller.replacePresentationPolicy(PresentationPolicy.unavailable())
        setup.recorder.cleanup = AudioCleanup(true)
        setup.controller.discardRecording()
        assertFalse(setup.controller.voiceState.value.cleanupRequired)
        assertEquals("Local recording discarded.", setup.controller.voiceState.value.notice)
        setup.controller.close()
    }

    @Test fun recorderCleanupOverflowDisclosesRestartInsteadOfDiscardSuccess() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        setup.recorder.cleanup = AudioCleanup(false, restartRequired = true)
        setup.controller.discardRecording()
        assertTrue(setup.controller.voiceState.value.cleanupRequired)
        assertTrue(setup.controller.voiceState.value.error!!.contains("Force-stop"))
        assertNull(setup.controller.voiceState.value.notice)
        setup.controller.close()
    }

    @Test fun recorderCleanupDebtSurvivesAdapterReleaseUntilARealRetrySucceeds() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        setup.recorder.cleanup = AudioCleanup(false)
        setup.controller.releaseAudioResources()
        setup.controller.onForeground()
        setup.controller.discardRecording()
        assertTrue(setup.controller.voiceState.value.cleanupRequired)
        assertNull(setup.controller.voiceState.value.notice)
        setup.controller.startRecording()
        runCurrent()
        assertEquals(0, setup.recorder.starts)
        setup.recorder.cleanup = AudioCleanup(true)
        setup.controller.discardRecording()
        assertFalse(setup.controller.voiceState.value.cleanupRequired)
        setup.controller.close()
    }

    @Test fun recorderRestartLatchCannotDisappearWhenTheAdapterIsReleased() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        setup.recorder.cleanup = AudioCleanup(false, restartRequired = true)
        setup.controller.releaseAudioResources()
        setup.recorder.cleanup = AudioCleanup(true)
        setup.controller.discardRecording()
        assertTrue(setup.controller.voiceState.value.cleanupRequired)
        assertTrue(setup.controller.voiceState.value.error!!.contains("Force-stop"))
        setup.controller.close()
    }

    @Test fun lateCancelledStartCleanupCannotResurrectAnAdapterAfterClose() = runTest {
        val setup = setup()
        val finishCancelledStart = CompletableDeferred<Unit>()
        setup.recorder.delayedCancelledStart = finishCancelledStart
        setup.controller.onForeground()
        setup.controller.startRecording()
        runCurrent()
        assertEquals(1, setup.recorder.starts)
        setup.controller.close()
        setup.recorder.cleanup = AudioCleanup(false)
        finishCancelledStart.complete(Unit)
        runCurrent()
        assertEquals(1, setup.recorderCreations())
        assertTrue(setup.controller.voiceState.value.cleanupRequired)
        assertNull(setup.controller.voiceState.value.notice)
    }

    @Test fun lateStorageFailureAfterContextLossStillPublishesCleanupDebt() = runTest {
        val setup = setup()
        val finishFailedStart = CompletableDeferred<Unit>()
        setup.recorder.delayedCancelledStart = finishFailedStart
        setup.recorder.delayedStartFailure = IOException("private writer creation failure")
        setup.controller.onForeground()
        setup.controller.startRecording()
        runCurrent()
        setup.controller.replacePresentationPolicy(PresentationPolicy.unavailable())
        setup.controller.releaseAudioResources()
        setup.recorder.cleanup = AudioCleanup(false)
        finishFailedStart.complete(Unit)
        runCurrent()
        assertTrue(setup.controller.voiceState.value.cleanupRequired)
        assertNull(setup.controller.voiceState.value.notice)
        assertFalse(setup.controller.voiceState.value.error!!.contains("private"))
        setup.controller.startRecording()
        runCurrent()
        assertEquals(1, setup.recorder.starts)
        setup.recorder.cleanup = AudioCleanup(true)
        setup.controller.discardRecording()
        assertFalse(setup.controller.voiceState.value.cleanupRequired)
        setup.controller.close()
    }

    @Test fun lateStorageFailureAfterCloseCannotCreateAnotherAdapter() = runTest {
        val setup = setup()
        val finishFailedStart = CompletableDeferred<Unit>()
        setup.recorder.delayedCancelledStart = finishFailedStart
        setup.recorder.delayedStartFailure = IOException("private writer creation failure")
        setup.controller.onForeground()
        setup.controller.startRecording()
        runCurrent()
        setup.controller.close()
        setup.recorder.cleanup = AudioCleanup(false)
        finishFailedStart.complete(Unit)
        runCurrent()
        assertEquals(1, setup.recorderCreations())
        assertEquals(1, setup.recorder.starts)
        assertTrue(setup.controller.voiceState.value.cleanupRequired)
        assertNull(setup.controller.voiceState.value.notice)
    }

    @Test fun transferredDeletionFailureIsRetainedAlongsidePartialCleanup() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        setup.controller.startRecording()
        runCurrent()
        val file = RefusingFile()
        setup.recorder.result.complete(RecordedAudio(file, 500, 16044))
        runCurrent()
        setup.controller.discardRecording()
        assertTrue(setup.controller.voiceState.value.cleanupRequired)
        file.allowed = true
        setup.controller.discardRecording()
        assertFalse(setup.controller.voiceState.value.cleanupRequired)
        assertFalse(file.exists())
        setup.controller.close()
    }

    @Test fun playbackEndAndAsyncErrorClearRequestAndLateEventsCannotRepopulateContext() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        setup.controller.startRecording()
        runCurrent()
        setup.recorder.result.complete(RecordedAudio(absentRecording(), 500, 16044))
        runCurrent()
        setup.controller.replayRecording()
        val first = setup.player.event!!
        first(ReplayEvent.PLAYING)
        assertTrue(setup.controller.voiceState.value.replayPlaying)
        first(ReplayEvent.ENDED)
        assertFalse(setup.controller.voiceState.value.replayRequested)
        setup.controller.replayRecording()
        val second = setup.player.event!!
        second(ReplayEvent.FAILED)
        assertFalse(setup.controller.voiceState.value.replayRequested)
        assertNotNull(setup.controller.voiceState.value.error)
        setup.controller.replayRecording()
        val late = setup.player.event!!
        setup.controller.replacePresentationPolicy(PresentationPolicy.unavailable())
        late(ReplayEvent.PLAYING)
        assertFalse(setup.controller.voiceState.value.replayPlaying)
        assertNull(setup.controller.voiceState.value.recording)
        setup.controller.close()
    }

    @Test fun replacementDisposesPrivateStateAndFencesLateTransport() = runTest {
        val setup = setup()
        val late = CompletableDeferred<BridgeSession>()
        setup.transport.openResult = late
        setup.controller.onForeground()
        runCurrent()
        setup.controller.editDraft("private old-context draft")
        setup.controller.reviewWords(true)
        setup.controller.replacePresentationPolicy(PresentationPolicy.unavailable())
        late.complete(BridgeSession("old", "private", emptyList()))
        runCurrent()
        assertNull(setup.controller.bridgeState.value.sessionId)
        assertEquals("", setup.controller.bridgeState.value.draft)
        assertFalse(setup.controller.wordsReviewed.value)
        setup.controller.close()
    }

    @Test fun lateCaptureResultAfterReplacementIsDeletedAndNeverShown() = runTest {
        val setup = setup()
        setup.recorder.ignoreCancellation = true
        setup.controller.onForeground()
        setup.controller.startRecording()
        runCurrent()
        setup.controller.replacePresentationPolicy(PresentationPolicy.unavailable())
        val file = File.createTempFile("capture-late-test", ".wav")
        setup.recorder.result.complete(RecordedAudio(file, 500, 16044))
        runCurrent()
        assertFalse(file.exists())
        assertNull(setup.controller.voiceState.value.recording)
        setup.controller.close()
    }

    @Test fun stopReplayCannotOrphanAnActiveCapture() = runTest {
        val setup = setup()
        setup.controller.onForeground()
        setup.controller.startRecording()
        runCurrent()
        setup.controller.stopReplay()
        setup.recorder.result.complete(RecordedAudio(absentRecording(), 500, 16044))
        runCurrent()
        assertEquals(CapturePhase.IDLE, setup.controller.voiceState.value.phase)
        assertNotNull(setup.controller.voiceState.value.recording)
        setup.controller.close()
    }

    private data class Setup(
        val controller: CompanionController,
        val transport: FakeTransport,
        val recorder: FakeRecorder,
        val player: FakePlayer,
        val recorderCreations: () -> Int,
    )
    private fun TestScope.setup(policy: PresentationPolicy = PresentationPolicy.developmentFixture()): Setup {
        val transport = FakeTransport()
        val recorder = FakeRecorder()
        val player = FakePlayer()
        var creations = 0
        return Setup(CompanionController(BridgeStore(transport), this, { creations += 1; recorder }, { player }, { testScheduler.currentTime }, PresentationGate(policy)), transport, recorder, player, { creations })
    }

    private class FakeTransport : BridgeTransport {
        var opens = 0
        var reads = 0
        var submits = 0
        var openResult: CompletableDeferred<BridgeSession>? = null
        override suspend fun openSession(): BridgeSession {
            opens += 1
            return openResult?.await() ?: BridgeSession("fixture-$opens", "fixture", emptyList())
        }
        override suspend fun session(sessionId: String): BridgeSession {
            reads += 1
            return BridgeSession(sessionId, "fixture", emptyList())
        }
        override suspend fun submit(sessionId: String, requestId: String, text: String): SubmittedTurn {
            submits += 1
            return SubmittedTurn(requestId, "fixture-run")
        }
        override fun close() = Unit
    }

    private class FakeRecorder : LocalRecorder {
        var starts = 0
        var stops = 0
        var cleanup = AudioCleanup(true)
        val cleanupResults = ArrayDeque<AudioCleanup>()
        var result = CompletableDeferred<RecordedAudio?>()
        var ignoreCancellation = false
        var delayedCancelledStart: CompletableDeferred<Unit>? = null
        var delayedStartFailure: Exception = CancellationException("Cancelled IO start finished disposing its partial file")
        override suspend fun start() {
            starts += 1
            delayedCancelledStart?.let {
                withContext(NonCancellable) { it.await() }
                throw delayedStartFailure
            }
        }
        override suspend fun awaitRecording(): RecordedAudio? = if (ignoreCancellation) withContext(NonCancellable) { result.await() } else result.await()
        override fun requestStop() { stops += 1 }
        private fun nextCleanup() = cleanupResults.removeFirstOrNull() ?: cleanup
        override fun cancel() = nextCleanup()
        override fun retryCleanup() = nextCleanup()
        override fun close() = Unit
    }

    private class FakePlayer : LocalPlayer {
        var plays = 0
        var event: ((ReplayEvent) -> Unit)? = null
        override fun play(file: File, onEvent: (ReplayEvent) -> Unit) { plays += 1; event = onEvent }
        override fun stop() = Unit
        override fun close() = Unit
    }

    private class RefusingFile : File("capture-refusing-controller-test.wav") {
        var allowed = false
        private var present = true
        override fun exists() = present
        override fun delete(): Boolean { if (!allowed) return false; present = false; return true }
    }

    private fun absentRecording() = File("absent-controller-recording.wav")
}
