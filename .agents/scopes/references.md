# Local References Scope

## Trigger

Load this scope only after the primary task scope when an external implementation, protocol,
research project, benchmark, or worked example would materially improve the task. The operator has
assigned the checkout-local `.agents/references/` shelf for this bounded use.

The shelf is ignored and may be absent, stale, incomplete, locally modified, or unavailable in
another checkout. Its contents are optional probes: never architecture, delivery evidence, a
dependency, or permission to copy an upstream design.

## Progressive Use

1. Establish LychD truth from tracked docs, source, tests, lockfiles, and installed packages first.
2. Check that `.agents/references/index.md` and the selected reference exist.
3. Read this map's one-line description, then the selected repository's top-level README.
4. Search filenames or text before opening a subtree:

    ```bash
    rg --files .agents/references/<name>
    rg -n '<term>' .agents/references/<name>
    ```

5. Load only the smallest relevant documentation, source, example, test, protocol, or benchmark.
6. Verify claims against current primary upstream sources when freshness or correctness matters.
7. Record no local path, private modification, or ignored-shelf state as public project truth.

## Agent Systems and Cognition

| Reference | Cheapest edge | Useful when |
|---|---|---|
| `pydantic-ai` | `README.md`, then `docs/agents/`, `docs/graph/`, `docs/durable_execution/`, `docs/evals/`, or `docs/ui/` | Pydantic AI Agent, graph, durable execution, evaluation, MCP/A2A, approval, or event-stream behavior matters |
| `fasta2a` | `README.md`, then `fasta2a/` and focused tests | A2A task, storage, broker, worker, artifact, or ASGI behavior matters |
| `avp-spec` | `README.md`, `SPECIFICATION.md`, then `protocol/` or `schemas/` | Evaluating the experimental Agent Vector Protocol, latent/KV transfer, transport, or security contract |
| `avp-python` | `README.md`, then `docs/`, `src/avp/`, tests, or one benchmark | Inspecting an AVP implementation, connector, codec, context store, transport, or benchmark |
| `LatentMAS` | `README.md`, then `methods/` or `example_logs/` | Researching experimental latent-space multi-agent collaboration; never as established LychD capability |
| `Memori` | `README.md`, then `docs/features/`, `memori/memory/`, or one storage example | Comparing long-term memory, ingestion, retrieval, consolidation, or datastore boundaries |
| `adhd` | `README.md`, then `skills/adhd/SKILL.md`, `src/`, or `bench/` | Exploring divergent ideation, isolated parallel reasoning, critic passes, or creative-agent evaluation |
| `Gentle-Coding` | `README.md` | Examining the unverified hypothesis that coercive versus gentle prompt framing affects model behavior |
| `cwc-workshops` | `README.md`, then one named workshop | Looking for worked examples of agent decomposition, eval-driven development, memory, MCP, multi-agent streaming, or UI verification; upstream says the materials are unmaintained |

## Agent and Observability UX

| Reference | Cheapest edge | Useful when |
|---|---|---|
| `Hyvemind` | `README.md`, `docs/`, then `app/src/` | Comparing multi-model task conversations, swarms, code review, desktop agent orchestration, or visual execution UX |
| `cwc-workshops` | `production-ready-agent/` or `how-we-claude-code/` after the root README | Studying streamed agent events, gated tool calls, verifiable UI contracts, or human/agent design workflows |
| `svelte-stack.md` | Specialized [Svelte shelf index](../references/svelte-stack.md) | Any Svelte 5, SvelteKit, Svelte Flow, graph canvas, or official Svelte AI-tooling task |

Use these for interaction patterns only. ADR 15, semantic server contracts, accessibility,
authorization, and retained evidence remain LychD-owned.

## Backend, Workers, and Application Structure

| Reference | Cheapest edge | Useful when |
|---|---|---|
| `awesome-litestar` | `README.md` and its exact category | Discovering current Litestar ecosystem projects before verifying them at their primary source |
| `litestar-fullstack` | `README.md`, then `docs/usage/`, `src/app/`, or focused tests | Comparing Litestar, SQLAlchemy, SAQ, Structlog, Granian, CLI, auth, or deployment patterns; its React/Jinja frontend is not Altar guidance |
| `saq` | `README.md`, then `docs/`, `saq/queue/`, or tests | SAQ queue, worker, scheduling, Postgres/Redis, job status, retry, or web-monitor behavior matters |
| `pydantic-ai` | Select the matching public docs/source area above | Implementing the installed agent/graph runtime after checking `.venv` and the lockfile first |

## Local Inference, Hardware, and Packaging

| Reference | Cheapest edge | Useful when |
|---|---|---|
| `club-3090` | `README.md`, then the matching `docs/`, `docs/engines/`, or `models/<name>/` page | Comparing RTX 3090 serving, vLLM, llama.cpp, SGLang, long-context, VRAM, or benchmark recipes |
| `ramalama` | `README.md`, then one matching `docs/*.md`, source, or test | Comparing Podman-based model serving, image/model handling, CLI, Quadlet, or container behavior |
| `llm-compressor` | `pyproject.toml`, `quantize.py`, and `sparse_logs/` | Inspecting a local uncommitted GPTQ/llmcompressor experiment only; it has no upstream remote or committed history |
| `localllama-insights` | `README.md`, then one named article | Finding community leads about inference, quantization, or hardware; every claim is unverified Reddit-derived material |

Never promote a benchmark, hardware number, patch, or compatibility claim without reproducing or
checking the current primary source and LychD's operated substrate.

## Vision and Document Ingestion

| Reference | Cheapest edge | Useful when |
|---|---|---|
| `PaddleOCR` | `README.md`, then `docs/`, `paddleocr/`, `deploy/`, `api_sdk/`, `mcp_server/`, or one provided skill | OCR, document parsing, structured extraction, deployment, API, MCP, or vision-ingestion behavior matters |

## Frontend and Graph Rendering

The seven Svelte-related directories are routed through the specialized
[`svelte-stack.md`](../references/svelte-stack.md) index:

- `svelte`
- `sveltekit`
- `svelte-ai`
- `svelte-ai-tools`
- `svelte-docs`
- `svelte-flow-docs`
- `xyflow`

Load [`svelte.md`](svelte.md) first. It owns the official MCP/autofixer workflow and LychD's
Svelte-specific drift gates.

## Developer Workflow

| Reference | Cheapest edge | Useful when |
|---|---|---|
| `jujutsu-tutorial` | `README.md`, then one chapter under `src/` | A Jujutsu branching, conflict, sharing, customization, or real-world workflow question needs an example beyond project conventions |

## Shelf Maintenance

Any operation that adds, removes, renames, reclones, or materially repurposes a top-level
`.agents/references/` entry must, in the same task:

1. update `.agents/references/index.md` with exactly one row per top-level directory;
2. give it a one-line purpose, caveat, and progressive route;
3. update this scope if its domain or cheapest edge is not already represented;
4. add a specialized local index when one reference family needs several progressive levels;
5. verify every mapped path exists and compare the directory inventory with the index;
6. keep the shelf ignored and never introduce it as a build, test, packaging, or publication input.

Do not fetch, refresh, or mutate an upstream reference merely because it was consulted.
