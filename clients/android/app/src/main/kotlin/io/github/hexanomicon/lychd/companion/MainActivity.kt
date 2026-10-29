package io.github.hexanomicon.lychd.companion

import android.Manifest
import android.content.pm.PackageManager
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.runtime.getValue
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import io.github.hexanomicon.lychd.companion.core.presentation.CompanionAction
import io.github.hexanomicon.lychd.companion.core.presentation.OfferDecision
import io.github.hexanomicon.lychd.companion.ui.CompanionScreen
import io.github.hexanomicon.lychd.companion.ui.CompanionTheme

class MainActivity : ComponentActivity() {
    private val companion: CompanionViewModel by viewModels()
    private var foregroundGeneration = 0L
    private var permissionRequestGeneration: Long? = null
    private var permissionPolicyGeneration: Long? = null
    private var pendingPermissionStart: Long? = null
    private val microphonePermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        // Permission can return after a lifecycle transition; it never starts background capture.
        val policyGeneration = permissionPolicyGeneration
        if (permissionRequestGeneration == foregroundGeneration && policyGeneration != null &&
            companion.presentationState.value.decision(CompanionAction.START_RECORDING, policyGeneration) == OfferDecision.OFFERED &&
            lifecycle.currentState.isAtLeast(Lifecycle.State.STARTED)
        ) {
            if (granted) {
                if (lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) {
                    companion.startRecording(policyGeneration)
                } else {
                    pendingPermissionStart = policyGeneration
                }
            } else {
                companion.microphonePermissionDenied(policyGeneration)
            }
        }
        permissionRequestGeneration = null
        permissionPolicyGeneration = null
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val bridge by companion.bridgeState.collectAsStateWithLifecycle()
            val voice by companion.voiceState.collectAsStateWithLifecycle()
            val reviewed by companion.wordsReviewed.collectAsStateWithLifecycle()
            val presentation by companion.presentationState.collectAsStateWithLifecycle()
            val deviceStatus by companion.deviceStatusState.collectAsStateWithLifecycle()
            // Capture this render's value, not a delegated State getter read by a late callback.
            val renderGeneration = presentation.generation
            CompanionTheme {
                CompanionScreen(
                    presentation = presentation,
                    bridge = bridge,
                    voice = voice,
                    reviewed = reviewed,
                    deviceStatus = deviceStatus,
                    onRefreshDeviceStatus = companion::refreshDeviceStatus,
                    onAppSettings = ::openAppSettings,
                    onDraftChange = { companion.editDraft(it, renderGeneration) },
                    onReviewChange = { companion.reviewWords(it, renderGeneration) },
                    onSend = { companion.send(renderGeneration) },
                    onRefresh = { companion.refresh(renderGeneration) },
                    onNewConversation = { companion.newConversation(renderGeneration) },
                    onStartRecording = { requestRecording(renderGeneration) },
                    onStopRecording = companion::stopRecording,
                    onReplay = { companion.replayRecording(renderGeneration) },
                    onStopReplay = companion::stopReplay,
                    onDiscard = companion::discardRecording,
                )
            }
        }
    }

    private fun requestRecording(expectedGeneration: Long) {
        if (!BuildConfig.DEBUG || !lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) return
        val presentation = companion.presentationState.value
        if (presentation.decision(CompanionAction.START_RECORDING, expectedGeneration) != OfferDecision.OFFERED) return
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            companion.startRecording(expectedGeneration)
        } else {
            permissionRequestGeneration = foregroundGeneration
            permissionPolicyGeneration = presentation.generation
            microphonePermission.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    private fun openAppSettings() {
        if (!lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) return
        try {
            startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", packageName, null)))
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, "App settings are unavailable. Open Companion's permissions from Android Settings.", Toast.LENGTH_LONG).show()
        } catch (_: SecurityException) {
            Toast.makeText(this, "Android did not allow app settings to open. Review Companion's permissions in Settings.", Toast.LENGTH_LONG).show()
        }
    }

    override fun onResume() {
        super.onResume()
        companion.onForeground()
        val pending = pendingPermissionStart
        pendingPermissionStart = null
        if (pending != null &&
            companion.presentationState.value.decision(CompanionAction.START_RECORDING, pending) == OfferDecision.OFFERED &&
            checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
        ) {
            companion.startRecording(pending)
        }
    }

    override fun onStop() {
        foregroundGeneration += 1
        pendingPermissionStart = null
        permissionRequestGeneration = null
        permissionPolicyGeneration = null
        companion.onBackground()
        super.onStop()
    }

    override fun onDestroy() {
        companion.releaseAudioResources()
        super.onDestroy()
    }
}
