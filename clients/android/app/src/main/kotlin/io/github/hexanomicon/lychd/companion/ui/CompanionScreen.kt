package io.github.hexanomicon.lychd.companion.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.progressBarRangeInfo
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import io.github.hexanomicon.lychd.companion.CapturePhase
import io.github.hexanomicon.lychd.companion.VoiceUiState
import io.github.hexanomicon.lychd.companion.core.BridgeState
import io.github.hexanomicon.lychd.companion.core.BridgeTurn
import io.github.hexanomicon.lychd.companion.core.diagnostics.DeviceStatus
import io.github.hexanomicon.lychd.companion.core.presentation.CompanionAction
import io.github.hexanomicon.lychd.companion.core.presentation.CompanionScreenId
import io.github.hexanomicon.lychd.companion.core.presentation.OfferDecision
import io.github.hexanomicon.lychd.companion.core.presentation.PolicySource
import io.github.hexanomicon.lychd.companion.core.presentation.PresentationState
import java.util.Locale

@Composable
fun CompanionScreen(
    presentation: PresentationState,
    bridge: BridgeState,
    voice: VoiceUiState,
    reviewed: Boolean,
    deviceStatus: DeviceStatus,
    onRefreshDeviceStatus: () -> Unit,
    onAppSettings: () -> Unit,
    onDraftChange: (String) -> Unit,
    onReviewChange: (Boolean) -> Unit,
    onSend: () -> Unit,
    onRefresh: () -> Unit,
    onNewConversation: () -> Unit,
    onStartRecording: () -> Unit,
    onStopRecording: () -> Unit,
    onReplay: () -> Unit,
    onStopReplay: () -> Unit,
    onDiscard: () -> Unit,
) {
    fun offers(action: CompanionAction) = presentation.decision(action) == OfferDecision.OFFERED
    fun shows(screen: CompanionScreenId) = presentation.decision(screen) == OfferDecision.OFFERED
    val conversationVisible = shows(CompanionScreenId.CONVERSATION)
    val wordsVisible = shows(CompanionScreenId.WORDS)
    val recordingVisible = shows(CompanionScreenId.LOCAL_RECORDING)
    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        LazyColumn(
            modifier = Modifier.fillMaxSize().safeDrawingPadding().imePadding(),
            contentPadding = PaddingValues(horizontal = 20.dp, vertical = 24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            item(key = "title") {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(
                        "Companion",
                        style = MaterialTheme.typography.headlineMedium,
                        modifier = Modifier.semantics { heading() },
                    )
                    Text("Device status and local tools.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            item(key = "device-status") {
                DeviceStatusPanel(deviceStatus, onRefreshDeviceStatus, onAppSettings)
            }
            if (presentation.policy.source == PolicySource.UNAVAILABLE) {
                item(key = "unavailable") {
                    StatusCard("Access is unavailable in this local context. A live connection has not been enabled.")
                }
            }
            if (presentation.policy.source == PolicySource.DEVELOPMENT_FIXTURE) {
                item(key = "fixture") {
                    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text("Development fixture", style = MaterialTheme.typography.titleSmall)
                            Text(
                                "Sample replies only. No live LychD connection or speech recognition. Microphone audio stays on this device.",
                                style = MaterialTheme.typography.bodyMedium,
                            )
                        }
                    }
                }
            }
            if (!conversationVisible && !wordsVisible && !recordingVisible &&
                presentation.policy.source == PolicySource.DEVELOPMENT_FIXTURE
            ) {
                item(key = "no-offers") { StatusCard("No working views are offered in this local context.") }
            }
            if (conversationVisible) {
                item(key = "conversation-controls") {
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        if (offers(if (bridge.sessionId == null) CompanionAction.OPEN_CONVERSATION else CompanionAction.REFRESH_CONVERSATION)) OutlinedButton(
                            onClick = onRefresh,
                            enabled = !bridge.busy,
                            modifier = Modifier.weight(1f).heightIn(min = 48.dp),
                        ) { Text("Refresh") }
                        if (offers(CompanionAction.OPEN_CONVERSATION)) OutlinedButton(
                            onClick = onNewConversation,
                            enabled = !bridge.busy,
                            modifier = Modifier.weight(1f).heightIn(min = 48.dp),
                        ) { Text("New conversation") }
                    }
                }
                if (bridge.busy) {
                    item(key = "bridge-progress") {
                        Column(
                            verticalArrangement = Arrangement.spacedBy(8.dp),
                            modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
                        ) {
                            Text("Waiting for the fixture…", style = MaterialTheme.typography.bodyMedium)
                            LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                        }
                    }
                }
                if (bridge.hasUncertainSubmission) {
                    item(key = "unknown-submission") {
                        StatusCard(
                            "Submission outcome unknown. Refresh can inspect the conversation, but cannot prove this send’s outcome. Start a new conversation before sending again.",
                            isError = true,
                        )
                    }
                }
                bridge.error?.let { error ->
                    item(key = "bridge-error") { StatusCard(error, isError = true) }
                }
                item(key = "conversation-heading") { SectionHeading("Conversation") }
                if (bridge.turns.isEmpty()) {
                    item(key = "empty-conversation") {
                        Text(
                            if (bridge.sessionId == null && offers(CompanionAction.OPEN_CONVERSATION)) "Opening a fixture conversation. Refresh or start a new conversation if it does not open."
                            else if (bridge.sessionId == null) "No conversation is available in this view. Opening one is not offered."
                            else "No messages yet. Enter words below to try the fixture.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
                itemsIndexed(bridge.turns, key = { index, _ -> "turn-$index" }) { _, turn ->
                    ConversationTurn(turn)
                }
            }
            if (recordingVisible || voice.phase != CapturePhase.IDLE || voice.recording != null || voice.cleanupRequired) {
                item(key = "voice") {
                    RecordingPanel(
                        voice = voice,
                        allowStart = offers(CompanionAction.START_RECORDING),
                        allowReplay = offers(CompanionAction.REPLAY_RECORDING),
                        onStart = onStartRecording,
                        onStop = onStopRecording,
                        onReplay = onReplay,
                        onStopReplay = onStopReplay,
                        onDiscard = onDiscard,
                    )
                }
            }
            if (wordsVisible) {
                item(key = "draft") {
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        SectionHeading(if (offers(CompanionAction.SEND_WORDS)) "Words to send" else "Words")
                        if (offers(CompanionAction.EDIT_WORDS)) OutlinedTextField(
                            value = bridge.draft,
                            onValueChange = onDraftChange,
                            modifier = Modifier.fillMaxWidth(),
                            label = { Text("Editable draft") },
                            supportingText = { Text("Enter or edit words manually. Recording does not transcribe them.") },
                            minLines = 3,
                            maxLines = 8,
                            enabled = !bridge.busy,
                        )
                        else SelectionContainer { Text(bridge.draft.ifBlank { "No words in this context." }) }
                        if (offers(CompanionAction.REVIEW_WORDS)) Row(
                            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).toggleable(
                                value = reviewed,
                                enabled = bridge.draft.isNotBlank() && !bridge.busy,
                                role = Role.Checkbox,
                                onValueChange = onReviewChange,
                            ).padding(end = 12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Checkbox(checked = reviewed, onCheckedChange = null, enabled = bridge.draft.isNotBlank() && !bridge.busy)
                            Text("I reviewed these words.", style = MaterialTheme.typography.bodyMedium)
                        }
                        if (offers(CompanionAction.SEND_WORDS)) Button(
                            onClick = onSend,
                            enabled = reviewed && bridge.draft.isNotBlank() && bridge.sessionId != null &&
                                !bridge.busy && !bridge.hasUncertainSubmission && voice.phase == CapturePhase.IDLE,
                            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
                        ) { Text("Send reviewed words") }
                        Text(
                            "Conversations and drafts are temporary. Restarting the app may clear them. Leaving this screen stops audio and attempts to discard its temporary files.",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ConversationTurn(turn: BridgeTurn) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (turn.role == "user") MaterialTheme.colorScheme.surfaceVariant else MaterialTheme.colorScheme.surface,
        ),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                when (turn.role) {
                    "user" -> "You"
                    "agent" -> "Fixture reply"
                    else -> "Fixture message"
                },
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            SelectionContainer { Text(turn.content, style = MaterialTheme.typography.bodyLarge) }
        }
    }
}

@Composable
private fun RecordingPanel(
    voice: VoiceUiState,
    allowStart: Boolean,
    allowReplay: Boolean,
    onStart: () -> Unit,
    onStop: () -> Unit,
    onReplay: () -> Unit,
    onStopReplay: () -> Unit,
    onDiscard: () -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            SectionHeading("Local microphone recording")
            Text(
                "Up to 15 seconds. No transcription or upload. Microphone access is requested when you start.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            when (voice.phase) {
                CapturePhase.IDLE -> {
                    if (allowStart) OutlinedButton(
                        onClick = onStart,
                        enabled = !voice.cleanupRequired,
                        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
                    ) {
                        Text(if (voice.recording == null) "Start recording" else "Record again")
                    }
                }
                CapturePhase.STARTING -> {
                    Text("Starting microphone…", modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
                    OutlinedButton(onClick = onStop, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Cancel recording") }
                }
                CapturePhase.RECORDING -> {
                    Text("Recording · ${seconds(voice.elapsedMillis)} / 15.0 seconds")
                    LinearProgressIndicator(
                        progress = { (voice.elapsedMillis / 15_000f).coerceIn(0f, 1f) },
                        modifier = Modifier.fillMaxWidth().semantics {
                            progressBarRangeInfo = ProgressBarRangeInfo((voice.elapsedMillis / 15_000f).coerceIn(0f, 1f), 0f..1f)
                        },
                    )
                    Button(onClick = onStop, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Stop recording") }
                }
                CapturePhase.STOPPING -> {
                    Text("Finishing local recording…", modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
                    LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                }
            }
            if (voice.cleanupRequired) {
                OutlinedButton(onClick = onDiscard, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Retry audio discard") }
            }
            voice.recording?.let { recording ->
                Text("Recorded locally · ${seconds(recording.durationMillis)} seconds", style = MaterialTheme.typography.bodyMedium)
                if (allowReplay) OutlinedButton(onClick = onReplay, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Replay local recording") }
                if (voice.replayRequested) {
                    Text(if (voice.replayPlaying) "Playing local recording." else "Local replay requested; playback is not active.", style = MaterialTheme.typography.bodySmall)
                    OutlinedButton(onClick = onStopReplay, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Stop replay") }
                }
                TextButton(onClick = onDiscard, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Discard local recording") }
            }
            voice.error?.let { StatusCard(it, isError = true) }
            voice.notice?.let {
                Text(it, style = MaterialTheme.typography.bodySmall, modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
            }
        }
    }
}

@Composable
private fun SectionHeading(text: String) {
    Text(text, style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { heading() })
}

@Composable
private fun StatusCard(text: String, isError: Boolean = false) {
    Card(
        modifier = Modifier.fillMaxWidth().semantics { liveRegion = LiveRegionMode.Polite },
        colors = CardDefaults.cardColors(
            containerColor = if (isError) MaterialTheme.colorScheme.errorContainer else MaterialTheme.colorScheme.surfaceVariant,
            contentColor = if (isError) MaterialTheme.colorScheme.onErrorContainer else MaterialTheme.colorScheme.onSurfaceVariant,
        ),
    ) { Text(text, modifier = Modifier.padding(16.dp), style = MaterialTheme.typography.bodyMedium) }
}

private fun seconds(millis: Long): String = String.format(Locale.getDefault(), "%.1f", millis / 1_000.0)
