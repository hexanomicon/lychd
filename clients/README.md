# Clients

`clients/` contains complete delivery-client project roots. Clients project the authoritative
LychD system under `src/lychd/`; they do not own capital-C Composition truth merely because they
have independent toolchains or release artifacts.

- `web/` is the SvelteKit Altar project.
- `android/` is reserved for the Android client; no Android application is delivered yet.

[ADR 01](../docs/adr/01-doctrine.md#repository-source-topology) owns this repository boundary, and
[ADR 15](../docs/adr/15-frontend.md) owns the web client.
