# Clients

`clients/` contains complete delivery-client project roots. Clients project the authoritative
LychD system under `src/lychd/`; they do not own capital-C Composition truth merely because they
have independent toolchains or release artifacts.

- `web/` is the SvelteKit Altar project.
- `minecraft/` is the opt-in Fabric server actuator for the experimental
  [Blockworld companion lab](../docs/compositions/blockworld/companion-lab.md).
- `minecraft-voice/` is its separate opt-in local voice-control client, with synthetic actual-client
  input and multilingual multiline-HUD checks; physical keys/focus and audio remain unqualified.
- `android/` is reserved for the native Android client for the [Companion Composition](../docs/compositions/companion/index.md);
  no Android application is delivered yet.

[ADR 01](../docs/adr/01-doctrine.md#repository-source-topology) owns this repository boundary, and
[ADR 15](../docs/adr/15-frontend.md) owns the web client.
