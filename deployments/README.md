# Host deployment assets

[Tumbleweed VPS](../docs/deployments/tumbleweed/index.md) covers the mutable host pilot and
[`ansible/`](ansible/README.md) provides its repeatable host and exact-source preparation.

[MicroOS VPS host](../docs/sepulcher/deployments.md) is the canonical runbook for one AlphaVPS
C6G pilot. It covers installer media, recovery, Btrfs layout, first-boot setup, host verification,
and the separate application qualification boundary.

[`microos/`](microos/README.md) contains the first-boot bundle and read-only verifier. Host setup
does not deliver automatic LychD deployment or qualify a complete application lifecycle.
