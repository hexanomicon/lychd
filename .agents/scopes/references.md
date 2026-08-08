# Local References Scope

## Trigger

Load only after the primary scope when an external implementation, protocol, research project,
benchmark, or example would materially improve the task. The ignored `.agents/references/` shelf
is optional and may be absent, stale, incomplete, or locally modified. It is never architecture,
delivery evidence, a dependency, or permission to copy upstream design.

## Progressive Use

1. Establish LychD truth from tracked docs, source, tests, lockfiles, and installed packages first.
2. Check `.agents/references/index.md` and the selected reference, then read its one-line
   description and top-level README.
3. Search before opening a subtree:

    ```bash
    rg --files .agents/references/<name>
    rg -n '<term>' .agents/references/<name>
    ```

4. Load the smallest relevant documentation, source, example, test, protocol, or benchmark.
5. Verify current primary upstream sources when freshness or correctness matters.
6. Never publish local paths, private modifications, or ignored-shelf state as project truth.

## Agent Systems and Cognition

| Reference | Cheapest edge | Useful when |
|---|---|---|
| `pydantic-ai` | `README.md`, then `docs/agents.md`, `docs/graph/`, `docs/durable_execution/`, `docs/evals/`, or `docs/ui/` | Pydantic AI Agent, graph, durable execution, evaluation, MCP/A2A, approval, or event-stream behavior matters |
| `deepfabric` | `README.md`, then `docs/`, `src/`, or one focused evaluation path | Comparing synthetic-data admission, real tool execution, training preparation, or evaluation without treating generated traces as truth |
| `fasta2a` | `README.md`, then `fasta2a/` and focused tests | A2A task, storage, broker, worker, artifact, or ASGI behavior matters |
| `avp-spec` | `README.md`, `SPECIFICATION.md`, then `protocol/` or `schemas/` | Evaluating the experimental Agent Vector Protocol, latent/KV transfer, transport, or security contract |
| `avp-python` | `README.md`, then `docs/`, `src/avp/`, `tests/`, or `benchmarks/` | Inspecting an AVP implementation, connector, codec, context store, transport, or benchmark |
| `LatentMAS` | `README.md`, then `methods/` or `example_logs/` | Researching experimental latent-space multi-agent collaboration; never as established LychD capability |
| `Memori` | `README.md`, then `docs/features/`, `memori/memory/`, or `examples/` | Comparing long-term memory, ingestion, retrieval, consolidation, or datastore boundaries |
| `adhd` | `README.md`, then `skills/adhd/SKILL.md`, `src/`, or `bench/` | Exploring divergent ideation, isolated parallel reasoning, critic passes, or creative-agent evaluation |
| `Gentle-Coding` | `README.md` | Examining the unverified hypothesis that coercive versus gentle prompt framing affects model behavior |
| `cwc-workshops` | `README.md`, then one named workshop | Looking for worked examples of agent decomposition, eval-driven development, memory, MCP, multi-agent streaming, or UI verification; upstream says the materials are unmaintained |

## Agent and Observability UX

| Reference | Cheapest edge | Useful when |
|---|---|---|
| `Hyvemind` | `README.md`, `docs/`, then `app/src/` | Comparing multi-model task conversations, swarms, code review, desktop agent orchestration, or visual execution UX |
| `cwc-workshops` | `production-ready-agent/` or `how-we-claude-code/` after the root README | Studying streamed agent events, gated tool calls, verifiable UI contracts, or human/agent design workflows |
| `svelte-stack.md` | Specialized [Svelte shelf index](../references/svelte-stack.md) | Any Svelte 5, SvelteKit, Svelte Flow, graph canvas, or official Svelte AI-tooling task |

These offer interaction patterns only. ADR 15 and LychD contracts still own accessibility,
authorization, semantics, and retained evidence.

## Backend, Workers, and Application Structure

| Reference | Cheapest edge | Useful when |
|---|---|---|
| `litestar` | `README.md`, then `docs/`, `litestar/`, or focused tests at the installed tag | Exact Litestar application, middleware, OpenAPI, dependency, exception, or lifecycle behavior matters |
| `advanced-alchemy` | `README.md`, then `docs/`, `advanced_alchemy/`, or focused tests | Exact async repository, service, transaction, migration-plugin, or Litestar integration behavior matters |
| `litestar-saq` | `README.md`, then `docs/`, `litestar_saq/`, or focused tests | Exact Litestar worker startup, shutdown, queue, process, or lifespan behavior matters |
| `awesome-litestar` | `README.md` and its exact category | Discovering current Litestar ecosystem projects before verifying them at their primary source |
| `litestar-fullstack` | `README.md`, then `docs/usage/`, `src/app/`, or focused tests | Comparing Litestar, SQLAlchemy, SAQ, Structlog, Granian, CLI, auth, or deployment patterns; its React/Jinja frontend is not Altar guidance |
| `saq` | `README.md`, then `docs/`, `saq/queue/`, or tests | SAQ queue, worker, scheduling, Postgres/Redis, job status, retry, or web-monitor behavior matters |
| `sqlalchemy` | `README.rst`, then `doc/`, `lib/sqlalchemy/`, or focused tests | Exact async transaction, row-lock, session, engine, pool, dialect, or ORM behavior matters |
| `alembic` | `README.rst`, then `docs/`, `alembic/`, or focused tests | Migration ordering, online/offline execution, revision graphs, or transactional DDL behavior matters |
| `testcontainers-python` | `README.md`, then `docs/`, `core/`, or the Postgres module | A real disposable PostgreSQL acceptance harness is being designed or diagnosed |
| `pydantic-ai` | Select the matching public docs/source area above | Implementing the installed agent/graph runtime after checking `.venv` and the lockfile first |

## Containment and Host Runtime

| Reference | Cheapest edge | Useful when |
|---|---|---|
| `nono` | `README.md`, then `docs/`, `crates/`, or focused tests | Designing or verifying Coffin filesystem, network, credential, process-tree, audit, or rollback containment |
| `podman` | `README.md`, then `docs/`, `cmd/podman/`, or focused tests | Exact rootless Podman, Quadlet, container lifecycle, socket, or systemd integration behavior matters |
| `playwright` | `README.md`, then `docs/src/`, `packages/playwright-test/`, or focused tests | Real-browser acceptance, accessibility, routing, focus, screenshots, or cross-engine behavior matters |

## Web Acquisition and Browser Services

| Reference | Cheapest edge | Useful when |
|---|---|---|
| `searxng` | `README.rst`, then `docs/dev/engines/`, `searx/`, or focused tests | Comparing self-hosted metasearch, engine adapters, query fan-out, result normalization, failure suspension, or JSON API behavior |
| `crawl4ai` | `README.md`, `CHANGELOG.md`, `SECURITY.md`, then `deploy/docker/`, `crawl4ai/`, or focused security tests | Evaluating a browser-backed self-hosted crawl/extraction API; pin the reviewed revision and inspect current advisories before any trial |
| `firecrawl` | `README.md`, `SELF_HOST.md`, `docker-compose.yaml`, then `apps/api/` or focused tests | Comparing OSS/cloud search, scrape, crawl, render, extraction, custody, queue, and provider-evidence boundaries |
| `browserless` | `README.md`, `LICENSE`, then `src/`, `docker/`, or focused tests | Comparing self-hosted browser/CDP/Playwright and REST rendering surfaces; SSPL/commercial terms and browser isolation remain separate gates |
| `tavily-python` | `README.md`, then `tavily/`, tests, and the current official API docs | Inspecting the client contract for Tavily Search/Extract/Crawl/Map; the closed provider implementation remains opaque |

These are mechanism references only. Scout and Webcrawler law still own effect separation,
destination authority, budgets, receipts, hostile-content fencing, and custody; Animator law owns
whether a local Soulstone or remote Portal may expose the typed capability.

## Local Inference, Hardware, and Packaging

| Reference | Cheapest edge | Useful when |
|---|---|---|
| `club-3090` | `README.md`, then the matching `docs/`, `docs/engines/`, or `models/<name>/` page | Comparing RTX 3090 serving, vLLM, llama.cpp, SGLang, long-context, VRAM, or benchmark recipes |
| `ramalama` | `README.md`, then one matching `docs/*.md`, source, or test | Comparing Podman-based model serving, image/model handling, CLI, Quadlet, or container behavior |
| `llama.cpp` | `README.md`, then `docs/`, `examples/`, or focused server tests | Exact llama.cpp build, server API, model loading, multimodal, cancellation, or runtime behavior matters |
| `vllm` | `README.md`, then `docs/`, `vllm/`, or focused tests | Exact vLLM serving, scheduling, OpenAI-compatible API, resource, or model behavior matters |
| `sglang` | `README.md`, then `docs/`, `python/sglang/`, or focused tests | Exact SGLang serving, scheduling, API, resource, or model behavior matters |
| `exllamav3` | `README.md`, then `docs/`, source, or focused tests | Exact ExLlamaV3 model, quantization, cache, server, or runtime behavior matters |
| `llm-compressor` | `pyproject.toml`, `quantize.py`, and `sparse_logs/` | Inspecting a local uncommitted GPTQ/llmcompressor experiment only; it has no upstream remote or committed history |
| `localllama-insights` | `README.md`, then one named article | Finding community leads about inference, quantization, or hardware; every claim is unverified Reddit-derived material |

Reproduce or check the primary source and LychD substrate before promoting any benchmark, hardware
number, patch, or compatibility claim.

## Vision and Document Ingestion

| Reference | Cheapest edge | Useful when |
|---|---|---|
| `PaddleOCR` | `README.md`, then `docs/`, `paddleocr/`, `deploy/`, `api_sdk/`, `mcp_server/`, or `skills/` | OCR, document parsing, structured extraction, deployment, API, MCP, or vision-ingestion behavior matters |

## Frontend and Graph Rendering

Route the five current Svelte directories through
[`svelte-stack.md`](../references/svelte-stack.md):

- `svelte`
- `sveltekit`
- `svelte-ai-tools`
- `svelte-docs`
- `xyflow`

Load [`svelte.md`](svelte.md) first for the official MCP/autofixer workflow and LychD drift gates.

## Developer Workflow

| Reference | Cheapest edge | Useful when |
|---|---|---|
| `jujutsu-tutorial` | `README.md`, then one chapter under `src/` | A Jujutsu branching, conflict, sharing, customization, or real-world workflow question needs an example beyond project conventions |

## Shelf Maintenance

Adding, removing, renaming, recloning, or repurposing a top-level `.agents/references/` entry
requires the same task to:

1. update `.agents/references/index.md` with exactly one row per top-level directory;
2. give it a one-line purpose, caveat, and progressive route;
3. update this scope if its domain or cheapest edge is not already represented;
4. add a specialized local index when one reference family needs several progressive levels;
5. verify every mapped path exists and compare the directory inventory with the index;
6. keep the shelf ignored and never introduce it as a build, test, packaging, or publication input.

Do not fetch, refresh, or mutate an upstream reference merely because it was consulted.
