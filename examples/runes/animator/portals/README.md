# Portal Runes

Portals declare remote Animator services reached through network APIs. These examples describe
an OpenAI Portal (`openai/main.toml`) and Gemini through Google's OpenAI-compatible endpoint
(`google-gemini/main.toml`).

`portals/` is a branch anchor; each concrete provider leaf owns its TOML. The
[Portal guide](../../../../docs/sepulcher/animator/portal.md) explains declaration and admission.
Current dispatch quarantines Portal issue, and the general privacy/egress path remains designed;
[State of Work](../../../../docs/state-of-the-work.md#animator-dispatch-spine) records that limit.
A stored declaration alone cannot enable a remote request.
