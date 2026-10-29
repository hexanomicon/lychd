package io.github.hexanomicon.lychd.companion.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import io.github.hexanomicon.lychd.companion.core.diagnostics.DeviceStatus
import io.github.hexanomicon.lychd.companion.core.diagnostics.DiagnosticRemedy
import io.github.hexanomicon.lychd.companion.core.diagnostics.diagnose

@Composable
internal fun DeviceStatusPanel(status: DeviceStatus, onRefresh: () -> Unit, onAppSettings: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Device status", style = MaterialTheme.typography.titleMedium, modifier = Modifier.semantics { heading() })
            Text("Local checks on this phone. Refresh samples conditions; it does not repair them or send data to LychD.",
                style = MaterialTheme.typography.bodySmall)
            OutlinedButton(onClick = onRefresh, enabled = !status.refreshing, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                Text("Refresh device status")
            }
            if (status.refreshing) {
                Text("Checking local device conditions…")
                LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            }
            if (status.refreshFailed) Text("The refresh did not complete. Earlier readings remain stale; try Refresh.",
                color = MaterialTheme.colorScheme.error)
            val snapshot = status.snapshot
            if (snapshot == null) {
                Text("No device snapshot yet. Checks run while Companion is in the foreground.")
            } else {
                Text(if (status.stale) "Earlier snapshot · refresh before relying on these readings." else
                    "Snapshot from the last refresh · conditions may have changed.", style = MaterialTheme.typography.bodySmall)
                Text("Android API ${snapshot.apiLevel}", style = MaterialTheme.typography.labelLarge)
                for (check in diagnose(snapshot)) {
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(check.title, style = MaterialTheme.typography.titleSmall, modifier = Modifier.semantics { heading() })
                        Text(check.observation, style = MaterialTheme.typography.bodyMedium)
                        Text(check.nextStep, style = MaterialTheme.typography.bodySmall,
                            color = if (check.needsAttention) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant)
                        if (check.remedy == DiagnosticRemedy.OPEN_APP_SETTINGS && !status.stale && !status.refreshing) {
                            TextButton(onClick = onAppSettings, modifier = Modifier.heightIn(min = 48.dp)) { Text("Open app settings") }
                        }
                    }
                }
            }
            Text("Live LychD connection is not configured in this build. Local diagnostics do not test host connectivity.",
                style = MaterialTheme.typography.bodySmall)
        }
    }
}
