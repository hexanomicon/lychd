# Deployment candidate verification — 9 November 2026

This records source checks, not an installed-host qualification. The starting integration source
was `e3a0912112957b077171eac3e317382e281a1b39`; reviewed
[PR #136](https://github.com/hexanomicon/lychd/pull/136), by `morichika33`, supplied candidate
`d73180cfbc72057b46a5957906910e47544a9cb3`. Coordination observations covered that open draft,
its empty review/comment timeline, and the #133 coordination timeline on 9 November. The
operator assigned this work directly; this campaign posted no remote claim or review.

Three independent design investigations covered installation, workstation provisioning and
network/access ownership using primary upstream sources. Their candidate files were reviewed
before integration. Subsequent independent source reviews found the external OCI descriptor and
sudo-password transition defects below; both were repaired and the repair reviewed. A separate
workstation review found inherited Starship initialization failure, also repaired.

## Passed source checks

- `bash deployments/check.sh /absolute/controller`: **149 tests** (127 Ansible/helper, 20
  AutoYaST, two forwarding-wrapper cases), standalone Ruff lint/format, and syntax/example-host
  selection for all ten playbooks. No target was contacted. Optional prerequisite bootstrap
  received separate source review; installed reload, policy and package effects remain unqualified.
- Fish syntax and an actual parent/child interactive-shell smoke with synthetic initialization:
  inherited managed prompt initializes; a foreign explicit prompt stays preserved.
- All generated module fragments for BIOS Server, UEFI Server and UEFI workstation passed
  supplemental Relax NG validation. This combined public core schema source
  [`a6aa77a`](https://github.com/yast/yast-autoinstallation/tree/a6aa77a10fc0f6f5e3040794d70d0f9001663c1f/src/autoyast-rnc)
  with installed Tumbleweed YaST module schemas (network 5.0.7, users 5.0.9, bootloader 5.0.42,
  security 5.0.6, services-manager 5.0.3, firewall 5.0.2, country 5.0.5). This caught and repaired
  the Btrfs list item spelling. It is **not** matching-installer validation or a boot receipt.
- Clean locked Zensical build, changed local documentation links and `git diff --check`.

PR repairs also cover foreign imported OCI tags, duplicate/link/foreign tar metadata, external
or embedded descriptor content, all-four-unit startup convergence, read-only source verification
before executing the CLI, redirect refusal before local Basic credentials could leave loopback,
and the controller/target uv 0.13.4 pin. Negative tests use synthetic
keys, credentials and local archive fixtures; no credential or real infrastructure inventory is
stored in this candidate.

## Gates that could not execute

The required OCI State test and existing HTTP authentication/Host/Origin/CSRF selection were
attempted through the maintained `make test` entry point. Podman failed before test execution
because its delegated cgroup exposed only `pids`, while the required build needs memory/CPU
controllers. A resource-limited user scope did not supply the missing controllers.

The supported Docker alternative reached image construction but could not resolve PyPI for
the isolated Hatchling build dependency. A separate Docker runtime diagnostic also failed with
the installed containerd shim API mismatch. No daemon was restarted, no resource guard removed,
and no host-native Core-test fallback used. These Core checks are **not claimed passed**.
Repair the test host and repeat the original OCI checks before integration/promotion:

```bash
make test PYTEST_TARGETS="tests/architecture/test_state_of_work.py tests/web/test_local_access.py tests/web/test_http_boundary.py" N=0
```

## Required target acceptance

Run the [installation](../docs/deployments/tumbleweed/install.md),
[Server](../docs/deployments/tumbleweed/index.md),
[workstation](../docs/deployments/tumbleweed/workstation.md), and optional
[access](../docs/deployments/tumbleweed/access.md) procedures on explicitly selected targets.
Matching-media schema/VM installation, first/second real applies, rootless storage, laptop
hardware, confined two-endpoint/browser access, live revocation and recovery remain pending.
The contributor's five-VPS report is attributed evidence for its earlier source, not a receipt
for these changed bytes. No VPS, laptop OS, USB medium or existing application was changed here.

## Follow-up SecOps and usability review — 9 November 2026

The operator requested a second review and repairs. PR #136 was refreshed at the same head;
its comments and the #133 coordination timeline remained empty. Two independent read-only
reviews covered the admitted deployment source before separate candidate fixes and lead review.
The lead edited the access guide during review; source/test inputs remained unchanged during
those initial reviews. No LychD sandbox or independent human approval is claimed.

The review found and repaired:

- Verification discarded a supplied exact image ID on an already-running host.
- Failed runtime SSH could select host mutation without proving that the account was absent.
- The firewall guard rejected the stock IPv6 bootstrap policy but missed dormant policies that
  activate when the private interface is assigned. The new guard admits only exact vendor
  ICMPv6 semantics in both runtime and permanent state and refuses other policy objects.
- Immediate listener inspection could race fresh sshd startup; package installation also shared
  an unsuitable short command timeout. Fresh readiness is bounded and package work has its own
  30-minute ceiling; read-only verification does not restart anything.

Added separate verify/revoke playbooks, durable revocation before transport effects, and boot
fences on **both** SSH and the owned WireGuard instance. Repeated revoke completes a pending
closure; apply cannot restore revoked intent. An independent external revocation record is still
required when restoring older snapshots. Both transport lifetimes also bind to firewalld, so its
loss schedules transport shutdown; installed firewall-loss closure still needs a real observation.
Explicit playbooks fail missing/disabled intent rather
than reporting a skipped success.

Client preparation now renders private WireGuard, known-hosts and connection files without
network effects or replacement of different material. The forwarder uses an exact SSH host key,
only the selected device key, no password fallback, and an explicit up-WireGuard route preflight.
Private output/identity boundaries, source-tree refusal, repeat rendering, route fallback and
actual `ssh -G` handling of paths with spaces have fixture checks. Administrator and runtime SSH
identities in the Server procedure were also checked through `ssh -G`, without a connection.

**Passed:** 177 deployment tests (146 Ansible/helper, 20 AutoYaST, 11 client/forwarder), standalone
Ruff lint/format and all twelve playbook syntax/example-host checks. Changed local documentation
links and the clean locked Zensical build also pass. Candidate bytes received lead review and
independent focused client/lifecycle review; authored fixes are not presented as self-independent.

**Unavailable:** the maintained OCI State/authentication/HTTP selection was attempted again and
failed before tests at Podman's missing delegated memory cgroup. The earlier Docker/runtime
failures above were not repaired by restarting host services. No Core result or real VPN,
SELinux, browser, reboot or established-session revocation qualification is claimed. Follow the
access guide's two-device acceptance before adopting the profile as supported.
