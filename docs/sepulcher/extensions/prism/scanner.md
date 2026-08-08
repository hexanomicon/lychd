---
title: Scanner
icon: material/text-recognition
---

# :material-text-recognition: Scanner

Prism's **Scanner** contract is stable while OCR models, native parsers, PDF pipelines, and serving
projects evolve. LychD therefore does not make PaddleOCR, MinerU, Xberg, or Markdown the universal
document abstraction. Each enters through [Assimilation](../../../adr/35-assimilation.md) as a
candidate implementation and earns only the exact document tasks proved by its bake.

This survey was reviewed on **2026-08-07**. It records candidates, not delivery or automatic
fallback. Vision remains Partial and no OCR adapter ships today.

## What the Scanner route actually owes

Uploading a PDF to a local HTTP endpoint may be one request. The trustworthy seam around that call
is larger:

```text
authorized ArtifactRef
→ bounded materialization and hostile-document inspection
→ exact Scanner task, engine, model, options, language and page range
→ local library, worker, CLI, REST job, MCP tool, or admitted Portal
→ validated page and region observations plus derivative artifacts
→ provenance, uncertainty, omissions, metrics and terminal receipt
```

`DocumentObservation@1` retains the source and derivative digests, page identity and geometry,
regions with boxes or polygons, semantic region class, extracted text, language, reading order,
confidence where the provider exposes it, tables, formulae, images, warnings, omitted or failed
pages, and the exact engine, model, configuration, and license profile. Markdown, HTML, searchable
PDF, and a provider's JSON tree are useful projections or derivatives; none is canonical source
truth.

Four offices must remain distinct:

| Office | Owns |
| --- | --- |
| Scanner semantic interface | tasks, request/result schemas, page/region meaning, omission and validation law |
| immutable capability profile | exact engine/model/pipeline revision, accepted media, languages, page/output limits, quality and license evidence |
| dialect driver | local call, CLI, REST, MCP, or provider-job encoding; timeout, error, cancellation, result, and reconciliation semantics |
| runtime adapter | Rune hydration, process/container plan, link and exact profile readiness, and optional activation |

A Prism-owned Scanner reference adapter may assemble those pieces, but its name does not collapse
their authority. A finite CLI/library path is a Spell-selected ToolProfile delivered into a trusted
executor or Tomb. A resident, queued, or remote service is an Animator reached through a
`CallGrant` or `JobGrant`. Asynchronous execution additionally uses Core's
[`ServiceJobAttempt@1`](../../../adr/14-workers.md#service-job-attempts-designed).

The host normally materializes authorized bytes and uploads them directly. A provider-visible file
URL is allowed only through a separate egress decision and must never become an ambient fetch or
SSRF path.

Engine and model remain separate even when a project bundles both. For a service, a Designed Rune
selects exact registered interface/profile/driver/dialect/evidence/resource definitions and pins
the deployment instance. For a finite tool, the Resolution Lock pins the ToolProfile instead.
Either way the closure retains pipeline or model, weights and digest, device/backend, languages,
optional modules, concurrency, memory envelope, and exact output fields that passed the bake.

## Three candidate routes

The projects overlap. The table names the office for which each is most interesting rather than
claiming that it can perform only one task.

| Candidate | Primary office and interface | License reading | Present judgment |
| --- | --- | --- | --- |
| [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | Direct OCR, PP-StructureV3 structured parsing, and PaddleOCR-VL; Python/CLI, self-hosted PaddleX REST, official hosted API, or MCP. | Apache-2.0 code; every selected model and dependency still needs its own receipt. | Primary first Scanner candidate. It covers multilingual text, coordinates, orientation, layout, tables, formulae, charts, reading order, and Markdown/JSON, but upstream breadth is not proof of reliability on LychD fixtures. |
| [Xberg](https://github.com/xberg-io/xberg) | Rust-first broad format detection and extraction with selective OCR, bindings, CLI, REST, and MCP. | MIT. | Promising native-extraction and routing candidate, especially when a born-digital document should avoid OCR. Xberg v1 is a fresh Kreuzberg rebrand, so it remains Lab material until soak, compatibility, and output-stability evidence exist. |
| [MinerU](https://github.com/opendatalab/MinerU) | Full PDF/image/Office parsing and reconstruction; CLI, Python, `/file_parse` asynchronous REST jobs, router, and VLM/OpenAI-server modes. | Current custom “MinerU Open Source License” adds commercial thresholds and online-service attribution to Apache-2.0. | Technically strong complex-document candidate, but the added use threshold is incompatible with a strict OSI/FOSS Core policy. Keep documented and license-gated unless its terms change or policy explicitly admits it. |

PaddleOCR remains a first-class, directly callable Scanner implementation even when Xberg or MinerU
can use OCR internally. A bundled dependency does not hide engine and model identity, prove the
direct profile, or prevent a Pattern from selecting PaddleOCR without the surrounding pipeline.

## Routing without a universal wrapper

The first routing study should compare explicit profiles rather than stack every project:

| Source and purpose | First candidates to bake |
| --- | --- |
| Born-digital PDF, Office file, or mixed collection of formats | Xberg native extraction and selective OCR; OCR stays off unless page evidence requires it. |
| Screenshot, photograph, or scan needing text regions | PaddleOCR direct, with the exact OCR or PP-StructureV3 profile pinned. |
| Multi-column report, table, formula, chart, or difficult mixed PDF | Compare PaddleOCR PP-StructureV3 or PaddleOCR-VL with MinerU. MinerU enters only through an explicit license gate, never as the strict-FOSS default. |

Fallback is not inferred from a low confidence value or parser failure. A Pattern may predeclare a
comparison or escalation branch with pinned implementations, or a failed attempt may settle and a
new forward Invocation may admit another extractor. Every result remains separately attributed;
agreement raises confidence only under an admitted comparison rule.

## Assimilation bake

The first corpus should include Slovak and English born-digital PDFs, clean and degraded scans,
rotated and warped pages, handwriting, receipts and forms, multi-column articles, tables, equations,
charts, footnotes, mixed-language pages, password-protected or malformed files, oversized images,
embedded attachments, links, scripts, and metadata. Synthetic fixtures provide exact truth;
operator-owned real documents test the distribution without entering a training corpus by accident.

Measure character and word error, page and region recall, coordinate error, reading-order edit,
table structure, formula equivalence, language routing, omissions, hallucinated text, derivative
fidelity, wall time, CPU/GPU memory, concurrency, cancellation, crash containment, restart, and
license closure. Promote profiles, not project logos: PaddleOCR may qualify for simple Slovak scans
while failing formulae; Xberg may qualify for native extraction but not difficult scans; MinerU may
win a bounded complex-PDF route without becoming admissible to strict-FOSS Core.

The pragmatic first bake compares exactly three profiles: PaddleOCR direct plus PP-StructureV3,
Xberg for broad native extraction and selective OCR, and MinerU for difficult documents behind its
license gate. Later candidates can enter through Assimilation without changing Prism's Scanner
contract or silently enlarging the initial Core.
