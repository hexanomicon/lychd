---
title: Coding-runtime research
icon: material/book-search
---

# Coding-runtime research

Research checked **15 October 2026** against the primary sources linked below. These observations
inform [Development bootstrap](development-bootstrap.md); they establish neither account
entitlement nor LychD implementation. Recheck provider behavior before a purchase, authentication
integration or runtime qualification. The Covenants and
[State of Work](../../../state-of-the-work.md) retain architecture and delivery authority.

## Recommended road and alternatives

Use the existing Codex application and requested Sol setting for the first bounded campaign.
Qualify the existing serial CLI protocol behind a trusted LychD host before adding a product-facing
app-server integration. Compare another reviewer on frozen cases before buying ongoing capacity.
This recommendation fits the present bootstrap constraints; no benchmark establishes a universally
best agent stack.

| Road | What the primary source establishes | Bootstrap decision |
| --- | --- | --- |
| Codex app with a goal | A durable objective continues across turns toward a verifiable stopping condition. [Goal guide](https://learn.chatgpt.com/docs/use-cases/follow-goals). | Start here. |
| Codex `exec` | Noninteractive jobs, JSONL events, output schemas, explicit sandbox settings and saved CLI authentication. [Guide](https://learn.chatgpt.com/docs/non-interactive-mode). | Smallest first foreign-runtime job. |
| Codex SDK | Programmatic Codex threads and streaming through official TypeScript and Python surfaces. [SDK guide](https://learn.chatgpt.com/docs/codex-sdk). | Consider when typed integration reduces actual work; avoid redundant layers. |
| Codex app-server | Bidirectional thread/turn protocol, steering, interruption and approval handling. [Protocol](https://learn.chatgpt.com/docs/app-server). | Add for a demonstrated persistent-session or interactive-product requirement. |
| OpenAI Agents SDK | Application-owned agent loop, handoffs and integration. [Runtime comparison](https://developers.openai.com/api/docs/guides/agents). | A distinct orchestration choice that cannot absorb LychD's owners. |
| OpenAI Agents API | Managed Codex harness, durable sessions and compaction/recovery; model usage is API-billed, with applicable tool/container costs. [Overview](https://developers.openai.com/api/docs/guides/agents-api/overview). | A later managed-server option, rather than the default way to spend app allowance. |
| Claude Code / Agent SDK | Programmatic coding and another provider's harness; supported authentication varies by mode. [Programmatic guide](https://code.claude.com/docs/en/headless), [SDK](https://code.claude.com/docs/en/agent-sdk/overview). | Optional comparison and separately qualified adapter. |

OpenAI's [platform engineering account](https://developers.openai.com/blog/codex-as-a-platform)
also distinguishes `exec` for bounded jobs, SDK workflows, and app-server for product clients.
Reusing a harness saves implementation; its private loop does not inherit LychD promotion,
credential or lifecycle authority.

## Sol, Ultra and allowance

The [model guide](https://learn.chatgpt.com/docs/models) names `gpt-6.1-sol` and distinguishes
Max's additional single-model reasoning from Ultra's use of subagents. Record the requested Sol
identifier and effective client settings; never silently substitute another model. Availability
still depends on client rollout and workspace/account controls.

The [Sol API page](https://developers.openai.com/api/docs/models/gpt-6.1-sol) lists reasoning
efforts through `max`, without an `ultra` effort. Ultrafast is a separate speed/service choice.
An app's Ultra selection therefore cannot be copied blindly into a raw Responses reasoning
field or CLI override. The adapter needs a reviewed mapping and must refuse unsupported settings.

The current [pricing guide](https://learn.chatgpt.com/docs/pricing) says Work and Codex share
subscription usage, while API prices are separate. Model, speed, task size and retained context
affect consumption. Allowance is not a fixed number of coding hours. Read actual usage and reset
windows; keep account balances outside public docs. Unused allowance authorizes no paid overflow.

The [noninteractive guide](https://learn.chatgpt.com/docs/non-interactive-mode) documents saved
CLI authentication and API-key alternatives. Its advanced ChatGPT-account CI credential-seeding
workflow excludes public/open-source repositories. That specific restriction does not prohibit
local coding against an open-source checkout. Do not copy personal tokens into shared/fork runners.

## Subscription-backed integration has a specific admission path

Avoid the outdated blanket claim that a ChatGPT subscription can never back an application call.
OpenAI documents a [Sign in with ChatGPT plan-usage preview](https://developers.openai.com/siwc/token-sharing-open-source)
for open-source and locally hosted apps, with client registration and host identity. Paid or
remotely hosted apps have a separate interest path. This is a provider integration to qualify,
not permission to extract an existing Codex session token.

The [preview limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
require streaming with storage disabled and client-owned HTTP history. Several fields and hosted
capabilities are excluded, including HTTP `multi_agent`, hosted MCP and native computer use.
Local harness orchestration is a different layer. Match required capabilities to the exact road.
The same preview rejects `max_output_tokens` and `max_tool_calls`. A wall deadline, usage snapshot
or captured token count is not a strict per-job token/credit cap. Required native ceilings need
separately qualified reservation/enforcement; if unavailable, that launch must refuse.

The [plan-usage app-server guide](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server)
warns that a bundled model catalogue is not an entitlement test: successful inference is needed
to prove request access. Metadata-only preparation cannot establish the whole model/billing path.

Use existing supported client authentication for operator/platform-controlled personal bootstrap.
This does not qualify a native Coffin launch: the current protocol supplies fresh homes without
provider credentials or an auth file and needs a reviewed Gate bridge admitting every child
provider request. Mounting the personal auth store into the guest cannot close that gap. Keep
the lifecycle in the external operator campaign if a supported credential-separated, bounded
provider road cannot yet be qualified. A distributed LychD offering
must separately qualify registration, per-user credentials, host identity, consent, revocation
and provider restrictions. Shared subscription pools and copied account sessions are not proposed.

## Continuous work needs a host and a stopping rule

[Long-running work](https://learn.chatgpt.com/docs/long-running-work) documents goal mode with
the same sandbox/approval boundaries and separate worktrees for parallel coding.
[Local scheduled tasks](https://learn.chatgpt.com/docs/automations) need the computer on, app
running and project available. These are wakeups, not an always-on server guarantee.

OpenAI's [long-horizon example](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex)
uses durable specifications, milestones, validation commands and recorded decisions/status.
Its reported long run is an example, not a general completion guarantee.

Anthropic's [effective-harness experiment](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
reports that compaction alone did not solve continuation; incremental features, explicit checks
and recoverable handoffs mattered. A later [harness-design experiment](https://www.anthropic.com/engineering/harness-design-long-running-apps)
finds evaluator separation useful near the generator's capability boundary, while some
scaffolding became overhead as models improved. The inference for LychD is to measure each extra
role and remove ceremony that does not improve accepted outcomes.

Anthropic's [multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
reports substantial token overhead and notes that tightly dependent coding parallelizes less
readily than research. This supports bounded independent panels, not a universal cost multiplier
or a claim that more agents always improve coding.

## Containment version selection {#containment-version-selection}

The 15 October review retires Security's former 0.66-series baseline without admitting a
replacement. Upstream's [DNS-before-admission advisory](https://github.com/nolabs-ai/nono/security/advisories/GHSA-gcpc-cqvp-h5c8)
and [same-port destination bypass](https://github.com/nolabs-ai/nono/security/advisories/GHSA-6hww-cch7-pfrh)
list affected versions through 0.73.0 and fixes at 0.74.0. Those published ranges include 0.66;
Landlock ABI 6+ alone does not dispose of the destination-address defect. Conversely, the older
[D-Bus advisory](https://github.com/nolabs-ai/nono/security/advisories/GHSA-27vp-2mmc-vmh3)
lists versions before 0.55.0, so it does not establish affectedness of 0.66. These are upstream
reports, not reproduced exploits against an admitted LychD profile.

Later metadata needs source resolution. The [endpoint advisory](https://github.com/nolabs-ai/nono/security/advisories/GHSA-8r33-hr9m-69wh)
lists the ordinary dot-segment fix at 0.73.0 while retaining an unresolved semicolon variant.
The [tool-shim advisory](https://github.com/nolabs-ai/nono/security/advisories/GHSA-wjv5-93q3-xm73)
uses a commit cutoff and an unreleased-fix field. The [0.78 release](https://github.com/nolabs-ai/nono/releases/tag/v0.78.0)
associates these advisories with that release, but association cannot silently repair the patch
fields. The [0.80 release](https://github.com/nolabs-ai/nono/releases/tag/v0.80.0) is a candidate
for review, not an approved version.

A bounded read-only study pinned 0.80 source commit
`8bb041356d48f771a221e58c98d9b1ff442e76fe`. Its
[endpoint policy](https://github.com/nolabs-ai/nono/blob/8bb041356d48f771a221e58c98d9b1ff442e76fe/crates/nono-proxy/src/config.rs)
contains dot-segment handling, ambiguous-path rejection and separator-aware globs; the inspected
[reverse-proxy path](https://github.com/nolabs-ai/nono/blob/8bb041356d48f771a221e58c98d9b1ff442e76fe/crates/nono-proxy/src/reverse.rs)
calls the policy before forwarding. The
[Linux entrypoint](https://github.com/nolabs-ai/nono/blob/8bb041356d48f771a221e58c98d9b1ff442e76fe/crates/nono-cli/src/tool-sandbox/platform/linux.rs)
and [shim](https://github.com/nolabs-ai/nono/blob/8bb041356d48f771a221e58c98d9b1ff442e76fe/crates/nono-cli/src/tool-sandbox/shim.rs)
contain a refusal path for recognized shim invocations whose broker context is missing. These
observations narrow the findings for the inspected paths. They establish neither the first fixed
release nor complete caller, launcher, policy, dependency or forwarding closure. The internal
child-launch path and its authority still need review. Embedded tests were not run; no downloaded
code was executed or installed.

Before host qualification, select one exact source and policy; disposition every applicable
advisory using inspected fixes and regressions or an enforced exclusion; bind that review to the
built executable and dependencies; then separately prove the actual containment and ceilings.
Missing effective CPU/memory files cannot be replaced by requested systemd properties. Keep
execution refused while any required qualification is unknown. The
[Security owner](../../../adr/09-security.md#the-coffin-delegated-agent-profile) retains that law;
this study delivers no Coffin, Provider Gate, native launcher or platform qualification.

## Whether to add Claude

Claude's [pricing page](https://claude.com/pricing) lists Pro at US$20 monthly and Max from
US$100 before applicable checkout differences. These are dated observations. Purchase only for
independently observed value within the actual total cost envelope.

[Pro/Max Code guidance](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan)
describes shared Claude/Claude Code usage windows and API keys selecting separate API billing.
Current [Agent SDK plan guidance](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan)
says SDK, `claude -p` and third-party app use may still draw plan limits; earlier announced
changes were paused. Do not assume the SDK is universally API-only.

The [monthly API credit policy](https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-and-team-plans),
changed on 7 October, describes eligible Max/Team credits and claim requirements. Those credits
are distinct from interactive subscription allowance and apply to the policy's eligible API use.
Buying a plan does not prove a particular adapter will draw those credits.

The [programmatic guide](https://code.claude.com/docs/en/headless) states that **bare mode does
not use subscription login** and requires supported API/provider credentials. The
[SDK overview](https://code.claude.com/docs/en/agent-sdk/overview) prohibits third-party developers
from offering claude.ai login/rate limits in products without prior approval. Personal operator
use and a distributed LychD authentication offering are separate decisions; isolation flags that
change billing must be qualified explicitly.

Trial a fresh Sol verifier first, then optional Claude against the same frozen diffs, acceptance
and total-budget envelope, with a protected answer key and separate confirmation cases. Adopt
another provider only for measured incremental benefit. This research bought or configured neither.

## Verify the road before first use

1. Read local CLI `--version`/`--help`; compare flags and wire format with the reviewed adapter.
   Here the available Codex binary reported **0.159.2**, matching the repository's reviewed Codex
   protocol. Help launched no agent and proves no provider access.
2. Inspect supported client model choices, settings, auth mode and usage without exposing secrets.
   App-server documents `account/read`, `account/rateLimits/read` and `model/list`; review the
   versioned [protocol](https://learn.chatgpt.com/docs/app-server) before calling them.
3. Select the exact personal-local, registered plan-usage or API road. Record missing entitlement
   and accounting evidence instead of inferring it from catalogue presence.
4. Qualify containment with an inert test executable, then admit one harmless bounded inference
   to prove model access, effective settings, usage attribution, output and cancellation.
5. Freeze runtime/policy identity and compatibility fixtures. Version, authentication, plan or
   protocol changes reopen affected qualification.

The repository's [CLI protocol](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/delegation/cli_protocol.py)
constructs command intent without a physical launcher. Limits cover wall time/capture; it emits
no reasoning-effort setting. Official provider features do not close these implementation gaps.

Reopen the recommendation when interactive approvals require app-server, explicitly chosen
server uptime justifies managed API costs, or matched review evidence earns another provider.
Revisit model/effort mapping and plan eligibility after provider changes, and agent count after
measured integration or review bottlenecks. None permits silent runtime fallback.
