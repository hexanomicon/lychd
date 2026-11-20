# Portal Runes

Portals declare remote Animator services. Choose one provider and one model explicitly. These
recipes assume a summoned Linux host with rootless Podman and an existing Codex.

## Choose a provider

- **OpenAI.** Create an [OpenAI project API key](https://developers.openai.com/api/docs/guides/api-keys)
  and use [`openai/main.toml`](openai/main.toml). Set `[[models]].id` to a model your project can
  use. For personal ChatGPT plan access in the Codex CLI, follow
  [Codex sign-in](https://learn.chatgpt.com/docs/auth?surface=cli).
- **OpenRouter.** Create an [OpenRouter API key](https://openrouter.ai/settings/keys) and use
  [`openai/openrouter.toml`](openai/openrouter.toml). The `openai` directory selects the
  OpenAI-compatible Rune schema. `provider_name = "openrouter"` selects the OpenRouter model
  profile. Keep the explicit `https://openrouter.ai/api/v1` base URL and choose an exact
  `author/model` ID from the [catalogue](https://openrouter.ai/models). The ID selects a model.
  OpenRouter still controls which upstream serves it under its
  [provider routing settings](https://openrouter.ai/docs/guides/routing/provider-selection).
- **Anthropic.** For a declaration targeting Anthropic's
  [OpenAI SDK compatibility endpoint](https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/openai-sdk),
  use [`openai/anthropic-compat.toml`](openai/anthropic-compat.toml) and a workspace-scoped Claude
  Console API key. LychD can parse and register this Chat Completions declaration. The live probe
  and generation are unverified. The native Messages API would require a Connector for that
  interface. For personal plan access, use the
  [Claude Code login](https://code.claude.com/docs/en/legal-and-compliance#authentication-and-credential-use).
- **Gemini.** Start with the [Gemini skeleton](google-gemini/main.toml). Add a `[[models]]` block
  with the Gemini model ID you chose before looking for a capability in LychD.

**OpenCode Go** has an official [client setup guide](https://opencode.ai/docs/console/harnesses).
In OpenCode, connect a Go workspace API key with `/connect` and choose the model with `/models`.
The Go API requires a session ID and documents a model inventory URL separate from the Chat
Completions base. The current LychD Portal has no Go session binding or separate inventory URL.
See the [Go API requirements](https://opencode.ai/docs/console/go/#endpoints).

## Load the Rune

1. Enable the `animator` built-in and run `lychd init` as shown in the
   [Portal guide](../../../../docs/sepulcher/extensions/animators/portal.md#1-admit-the-provider-schema).
2. Copy one file to the same relative path under the active Codex. For OpenRouter, run this from the
   repository root:

   ```bash
   CODEX_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/lychd"
   cp -i examples/runes/animator/portals/openai/openrouter.toml \
     "$CODEX_DIR/runes/animator/portals/openai/openrouter.toml"
   ```

3. Edit the copy and choose the model ID. Store the provider key as a
   [Podman secret](../../../../docs/sepulcher/extensions/animators/portal.md#2-seal-one-credential)
   using the name in `api_key_secret_name`. The TOML stores the name.
4. Run `uv run --extra postgres-binary lychd bind --dry-run`. Follow the
   [bind and readback procedure](../../../../docs/sepulcher/extensions/animators/portal.md#4-bind-restart-and-observe)
   to inspect `all_capabilities` at `/orchestrator/status` on the local Altar. With the OpenRouter
   sample ID, look for `openrouter-main:chat:openai/gpt-4o-mini` with phase `unknown`.

These recipes leave probes off. Current Core dispatch quarantines Portal grants. Bind and registry
readback verify the declaration locally. See
[State of Work](../../../../docs/state-of-the-work.md#animator-dispatch-spine) for remote dispatch
status.
