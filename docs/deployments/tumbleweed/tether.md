---
title: Native Tether pilot
icon: material/shield-link-variant-outline
---

# Native Tether on a fresh Server

Use this procedure to qualify one native private road to a fresh Tumbleweed Server: WireGuard
reaches a restricted SSH forwarder, which reaches the loopback Altar. It is for one instance
owner. The browser still needs its separate LychD Basic credential; this is not shared remote IAM.

The profile remains **Designed** pending complete installed qualification. [State of
Work](../../state-of-the-work.md#vpn-tether) owns that boundary; [Tether](../../sepulcher/extensions/tether.md)
explains the profile. Passing a command below does not establish browser, revocation or reboot
acceptance.

Keep provider-console recovery available and agree the recovery plan before starting Core:
public active-Vessel stop/restart remains incomplete. This procedure does not adopt an existing
active body or replace the separate infrastructure [access pilot](access.md).

## 1. Install and stop at the inactive bootstrap

Follow [AutoYaST installation](install.md) for the **Server** class, then the
[combined Server playbook](index.md#automate-one-host-end-to-end) with its pinned source and image.
Leave `lychd_app_start_authorized=false`, its default. The successful stopping point is
`bound_inactive`, before the first Core start. Do not run the guide's later authorized-start
invocation yet. Complete its host verification and direct runtime SSH checks first.

The remaining server commands run in a direct SSH login as **`lychd`**, without sudo, unless a
step explicitly says administrator. Set the same full public source SHA used by Ansible:

```bash
LYCHD_SOURCE_REV=FULL_40_CHARACTER_SHA
LYCHD_SOURCE="$HOME/src/lychd-$LYCHD_SOURCE_REV"
LYCHD_CLI="$LYCHD_SOURCE/.venv/bin/lychd"
CODEX_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/lychd"
TETHER_RECORDS="$HOME/.local/state/lychd-tether-pilot"
set -o pipefail
umask 077
mkdir -p "$TETHER_RECORDS"
cd "$LYCHD_SOURCE"
test "$(git rev-parse HEAD)" = "$LYCHD_SOURCE_REV"
git status --porcelain
"$LYCHD_CLI" status --json
"$LYCHD_CLI" run tether --help
```

Require the expected SHA, empty Git status and inactive body. An older CLI without `run tether` needs a fresh
source-matched installation; do not replace an interpreter beneath an active body.

## 2. Admit the UDP listener

**Administrator and provider control plane:** choose a distinct endpoint for this pilot. The
examples use UDP **51921**, server tunnel `10.203.72.1/32` and client `10.203.72.2/32`.
Confirm they do not overlap an existing network. Replace `203.0.113.10` below with the server's
actual reachable IPv4 address.

Permit UDP 51921 in any provider firewall. On the server, inspect active firewalld zones and
select the zone actually protecting the uplink. With firewalld already active, add only the
selected port to runtime and permanent policy:

```bash
sudo firewall-cmd --get-active-zones
TETHER_FIREWALL_ZONE=YOUR_VERIFIED_UPLINK_ZONE
sudo firewall-cmd --zone="$TETHER_FIREWALL_ZONE" --add-port=51921/udp
sudo firewall-cmd --permanent --zone="$TETHER_FIREWALL_ZONE" --add-port=51921/udp
```

Do not reload the whole firewall. Resolve inactive firewalld or conflicting policy separately
while retaining administrator access. The Ansible host floor supplies tools; it does not open
this native port. Tether has no privileged host-firewall channel. TCP 2222 stays inside the
tunnel; do not publish it on the host or provider firewall.

## 3. Build and pin the transport image

**Runtime `lychd`:** build from the same admitted source as the installed CLI. The build context
contains only four public source files and lives outside the checkout:

```bash
TETHER_BUILD_DIR=$(mktemp -d "${TMPDIR:-/tmp}/lychd-tether-build.XXXXXX")
install -m 0644 "$LYCHD_SOURCE/Containerfile.tether" "$TETHER_BUILD_DIR/Containerfile.tether"
install -D -m 0644 "$LYCHD_SOURCE/src/lychd/system/services/tether/runtime.py" \
  "$TETHER_BUILD_DIR/src/lychd/system/services/tether/runtime.py"
install -m 0644 "$LYCHD_SOURCE/LICENSE" "$TETHER_BUILD_DIR/LICENSE"
install -m 0644 "$LYCHD_SOURCE/THIRD_PARTY_NOTICES.md" "$TETHER_BUILD_DIR/THIRD_PARTY_NOTICES.md"
podman build --memory=768m --cpu-period=100000 --cpu-quota=100000 \
  --label "org.opencontainers.image.revision=$LYCHD_SOURCE_REV" \
  --tag "localhost/lychd-tether:$LYCHD_SOURCE_REV" \
  --file "$TETHER_BUILD_DIR/Containerfile.tether" "$TETHER_BUILD_DIR"
podman image inspect "localhost/lychd-tether:$LYCHD_SOURCE_REV" \
  --format '{{.Id}} {{.Digest}} {{index .Labels "org.opencontainers.image.revision"}}'
TETHER_DIGEST=$(podman image inspect "localhost/lychd-tether:$LYCHD_SOURCE_REV" --format '{{.Digest}}')
TETHER_IMAGE="localhost/lychd-tether@$TETHER_DIGEST"
podman image exists "$TETHER_IMAGE"
printf '%s\n' "$TETHER_IMAGE"
```

Require a nonempty `sha256:` manifest digest, the expected source label and a successful image
existence check. Record the output identity. Put this exact digest reference in the Rune;
neither the tag nor the configuration image ID substitutes for it. The build downloads the
Containerfile's declared base and packages. It needs no privileged container, host network,
Podman socket or home-directory mount.

## 4. Select Tether and write its Rune

**Runtime `lychd`:** in the existing `[extensions]` table of `$CODEX_DIR/lychd.toml`, change
`builtins` to `["tether"]` and retain `crypt = []`. Preserve the other generated settings,
including the pinned Core image. Then create the selected schema's anchor and inactive sample:

```bash
vi "$CODEX_DIR/lychd.toml"
"$LYCHD_CLI" init --dry-run
"$LYCHD_CLI" init
cat /proc/sys/kernel/random/uuid
vi "$CODEX_DIR/runes/tether/tethersettings.toml"
```

Use the displayed fresh UUID as `installation_id`. Replace the complete sample with the
following document, substituting that UUID, the real IPv4 address and the image reference printed
above. Remove the `# lychd: sample-rune` marker so the Rune becomes active. Keep exactly one
active TOML in this anchor.

```toml
installation_id = "YOUR_FRESH_INSTALLATION_UUID"
interface = "tether0"
server_address = "10.203.72.1/32"
udp_bind_address = "203.0.113.10"
udp_port = 51921
advertised_endpoint = "203.0.113.10:51921"
ssh_port = 2222

[quadlet]
image = "localhost/lychd-tether@sha256:YOUR_ACTUAL_MANIFEST_DIGEST"

[wireguard_secret]
purpose = "wireguard-server"
name = "lychd-tether-wg-server"

[ssh_host_secret]
purpose = "ssh-host"
name = "lychd-tether-ssh-host"
```

The UDP bind address must exist on this host; a provider's translated public endpoint can differ
from that bind address. Altar's port comes from the existing Settings, here 7134. There is no
separate Rune field for it. The two secret names must be absent and disjoint from Core secrets;
native preparation creates them rather than adopting keys by name.

From this edit onward, the combined `server.yml`/`deploy.yml` and `app-verify.yml` profile must
refuse the changed configuration: it accepts only original empty-extension settings. Use
`host.yml` and `verify.yml` for subsequent platform checks, and the native CLI for application
and Tether operations. Do not rewrite creation receipts to regain automation admission.

## 5. Prepare, bind the complete body, then start Core

**Runtime `lychd`:** discover the public plan without creating secrets:

```bash
"$LYCHD_CLI" run tether inspect --declared | tee "$TETHER_RECORDS/declared.json"
```

Copy `envelope.installation_id` and `envelope_digest` from that result into these variables.
Use a fresh operation UUID; retain it when repeating the same request after a clear refusal.

```bash
TETHER_INSTALLATION_ID=YOUR_DECLARED_INSTALLATION_UUID
TETHER_ENVELOPE_DIGEST=YOUR_DECLARED_ENVELOPE_DIGEST
TETHER_PREPARE_OP=$(cat /proc/sys/kernel/random/uuid)
"$LYCHD_CLI" run tether prepare --installation-id "$TETHER_INSTALLATION_ID" \
  --operation-id "$TETHER_PREPARE_OP" --expected-generation 0 \
  --envelope-digest "$TETHER_ENVELOPE_DIGEST" --dry-run
"$LYCHD_CLI" run tether prepare --installation-id "$TETHER_INSTALLATION_ID" \
  --operation-id "$TETHER_PREPARE_OP" --expected-generation 0 \
  --envelope-digest "$TETHER_ENVELOPE_DIGEST" | tee "$TETHER_RECORDS/preparation.json"
"$LYCHD_CLI" bind --dry-run
"$LYCHD_CLI" bind
"$LYCHD_CLI" start
"$LYCHD_CLI" status --json
```

Inspect each result before continuing. Preparation returns only server public identities and
fingerprints; retain the `wireguard-server` public key and `ssh-host` public key for the client.
Ordinary bind owns the complete Core, Tether, guard and closure-unit generation.

**Start Core before enrolling.** Generic system start requires every other owned unit inactive;
enrollment activates the Tether guard and transport. Starting Core first follows its migration
and Reactor dependencies without activating Tether. Check Core's status and logs before proceeding.

## 6. Generate client keys and enroll their public halves

**Client device, separately:** when ready to test, use standard WireGuard and OpenSSH tools.
Choose an unused private directory outside source checkouts and generate both keys locally;
do not overwrite existing keys:

```bash
umask 077
TETHER_CLIENT_DIR=$(mktemp -d "$HOME/lychd-tether-client.XXXXXX")
wg genkey > "$TETHER_CLIENT_DIR/wireguard.key"
wg pubkey < "$TETHER_CLIENT_DIR/wireguard.key" > "$TETHER_CLIENT_DIR/wireguard.pub"
ssh-keygen -t ed25519 -f "$TETHER_CLIENT_DIR/forward"
ssh-keygen -y -f "$TETHER_CLIENT_DIR/forward" > "$TETHER_CLIENT_DIR/forward.pub.bare"
cat "$TETHER_CLIENT_DIR/wireguard.pub" "$TETHER_CLIENT_DIR/forward.pub.bare"
```

`ssh-keygen -y` supplies the bare two-part public key that enrollment accepts, without the usual
`.pub` comment. Transfer only
these two public lines to the runtime terminal. Client private keys remain on the client;
the server neither generates nor exports them.

**Runtime `lychd`:** fill in those public lines, preview and enroll generation 1:

```bash
TETHER_PEER_WG_PUBLIC='YOUR_CLIENT_WIREGUARD_PUBLIC_KEY'
TETHER_PEER_SSH_PUBLIC='ssh-ed25519 YOUR_CLIENT_SSH_PUBLIC_KEY'
TETHER_ENROLL_OP=$(cat /proc/sys/kernel/random/uuid)
"$LYCHD_CLI" run tether enroll --installation-id "$TETHER_INSTALLATION_ID" \
  --operation-id "$TETHER_ENROLL_OP" --expected-generation 0 \
  --envelope-digest "$TETHER_ENVELOPE_DIGEST" --peer-id operator \
  --wireguard-public-key "$TETHER_PEER_WG_PUBLIC" --peer-address 10.203.72.2/32 \
  --ssh-public-key "$TETHER_PEER_SSH_PUBLIC" --dry-run
"$LYCHD_CLI" run tether enroll --installation-id "$TETHER_INSTALLATION_ID" \
  --operation-id "$TETHER_ENROLL_OP" --expected-generation 0 \
  --envelope-digest "$TETHER_ENVELOPE_DIGEST" --peer-id operator \
  --wireguard-public-key "$TETHER_PEER_WG_PUBLIC" --peer-address 10.203.72.2/32 \
  --ssh-public-key "$TETHER_PEER_SSH_PUBLIC" | tee "$TETHER_RECORDS/enrollment.json"
```

Require `complete: true`. Copy `request.intent_digest` from the result for subsequent inspection
and revocation; no internal hashing script is needed. If activation fails or its outcome is
uncertain, preserve the operation UUID and native receipts. Do not clear a fence or blindly
repeat enrollment: an interrupted activation reconciles toward closure.

## 7. Connect the client and open the Altar

**Client device:** create `$TETHER_CLIENT_DIR/tether.conf`, mode 0600, using its local private key,
the prepared server WireGuard public key and the actual UDP endpoint:

```ini
[Interface]
PrivateKey = YOUR_CLIENT_WIREGUARD_PRIVATE_KEY
Address = 10.203.72.2/32

[Peer]
PublicKey = YOUR_PREPARED_SERVER_WIREGUARD_PUBLIC_KEY
Endpoint = 203.0.113.10:51921
AllowedIPs = 10.203.72.1/32
PersistentKeepalive = 25
```

No DNS or default route is needed. Independently verify the prepared SSH host public key through
the existing trusted administrator/runtime connection. Put it in
`$TETHER_CLIENT_DIR/known_hosts` as one line:

```text
[10.203.72.1]:2222 ssh-ed25519 BASE64_FROM_PREPARED_SERVER_SSH_HOST_PUBLIC_KEY
```

Activate the client only when its network change is intended, then create the exact local forward:

```bash
sudo wg-quick up "$TETHER_CLIENT_DIR/tether.conf"
ssh -N -p 2222 -i "$TETHER_CLIENT_DIR/forward" \
  -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o ExitOnForwardFailure=yes \
  -o "UserKnownHostsFile=$TETHER_CLIENT_DIR/known_hosts" \
  -L 127.0.0.1:7134:127.0.0.1:7134 tether@10.203.72.1
```

Keep the SSH command running. On the server, obtain the separate application credential privately
with `"$LYCHD_CLI" access`; do not pipe that password into the trial record. In a dedicated browser
profile on the client, open **`http://127.0.0.1:7134`** and use that credential. Keep this exact
browser address so Host, Origin and the existing authentication/CSRF checks remain applicable.
This model-free installation can qualify application readback; it cannot answer chat.

## 8. Inspect, revoke and retain the result

**Runtime `lychd`:** use the enrollment result's exact intent digest:

```bash
TETHER_INTENT_DIGEST=YOUR_ENROLLMENT_REQUEST_INTENT_DIGEST
"$LYCHD_CLI" run tether inspect --installation-id "$TETHER_INSTALLATION_ID" \
  --operation-id "$(cat /proc/sys/kernel/random/uuid)" --expected-generation 1 \
  --envelope-digest "$TETHER_ENVELOPE_DIGEST" --intent-digest "$TETHER_INTENT_DIGEST"
TETHER_REVOKE_OP=$(cat /proc/sys/kernel/random/uuid)
"$LYCHD_CLI" run tether revoke --installation-id "$TETHER_INSTALLATION_ID" \
  --operation-id "$TETHER_REVOKE_OP" --expected-generation 1 \
  --envelope-digest "$TETHER_ENVELOPE_DIGEST" --intent-digest "$TETHER_INTENT_DIGEST" --dry-run
"$LYCHD_CLI" run tether revoke --installation-id "$TETHER_INSTALLATION_ID" \
  --operation-id "$TETHER_REVOKE_OP" --expected-generation 1 \
  --envelope-digest "$TETHER_ENVELOPE_DIGEST" --intent-digest "$TETHER_INTENT_DIGEST" \
  | tee "$TETHER_RECORDS/revocation.json"
```

Before revocation, require matching intent, prepared identities and attested runtime. Afterwards,
require `complete: true`, `closure.closed: true`, retained revocation evidence and no surviving
established forwarding session. Repeat inspection with the same generation/digests to observe
the fence and closed road. Incomplete closure stays fenced and needs reconciliation; never delete
its latch, generation or creation receipts.

On the client, end the SSH process and run `sudo wg-quick down "$TETHER_CLIENT_DIR/tether.conf"`
after the trial. Client teardown does not replace server revocation.

Retain observed browser/SSE behavior, wrong-credential and hostile-Origin refusal, denied
unrelated destinations and SSH channels, established-session revocation, guard/process failure,
tunnel loss and controlled reboot cases. Reboot recovery and persistence of a revoked fence still
require installed qualification; inspect and attempt reconnection after the authorized reboot
before claiming either property. [The acceptance boundary](../../sepulcher/extensions/tether.md#first-native-operator-profile)
lists the complete cases. A fresh next-generation enrollment requires a proven-cold road and
new operation identity; restoring whole state must not revive a revoked identity.
