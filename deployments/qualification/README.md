# Disposable Tumbleweed upgrade qualification

The [owning procedure](../../docs/deployments/tumbleweed/qualification.md) defines baseline
preparation, artifact trust, invocation, limits and receipt interpretation. `qualify.py --check`
and the tests are offline contracts. Only a complete real QEMU run can produce a passing
snapshot qualification receipt. No prebuilt baseline or disposable SSH private key is shipped.
