# Portal Runes

Portals are network/API-backed Animator declarations.

Current examples:

- `openai/main.toml`: OpenAI API Portal.
- `google-gemini/main.toml`: Gemini through Google's OpenAI-compatible endpoint.

`portals/` is only a branch; each provider leaf owns its TOML below that
directory. These examples do not make remote egress or a provider safe—consult
[State of Work](../../../../docs/state-of-the-work.md) before relying on either.
