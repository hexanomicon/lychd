---
title: 0. License
icon: material/link-variant
---

# :material-link-variant: 0. License

## Context

An operator must be able to compose private organs around LychD while sharing distributed
changes to its covered core. MPL-2.0 supplies that file-level boundary. This Covenant calls it
**the Iron Pact** and explains the choice; the binding text remains the repository
[LICENSE](https://github.com/hexanomicon/lychd/blob/main/LICENSE), which this ADR does not amend.

## Requirements

- Distributed modifications to covered core files remain open to their recipients.
- Separate, non-covered files can carry their own terms; private use, including intra-organization
  use, does not require publication.
- The project uses an OSI-approved license, and contributions enter and leave on the same terms.
- MPL's Secondary License compatibility remains available unless a later Covenant changes that
  choice.

## Options

| License family | Pressure that ruled it out |
| --- | --- |
| MIT / Apache-2.0 | Broad reuse, but a distributor may close modifications to the core itself. |
| AGPL-3.0 | Its network trigger is broader than the desired boundary for private and local composition. |
| LGPL-3.0 | Tuned to a library boundary, not this daemon and composed runtime. |
| BSL / SSPL / FSL | Use restrictions or non-OSI status conflict with the intended pact. |
| Unlicense / WTFPL | No chosen reciprocity, patent, or distribution terms. |
| MPL-2.0 | File-level reciprocity permits a Larger Work of genuinely separate files. |

## Decision

LychD is licensed under MPL-2.0. The project commits to keeping it free and open source.

The boundary follows covered source files. Distributed Source Code Form containing Covered
Software, including a Modification, stays MPL-2.0. When an executable contains Covered Software,
its distributor must make the corresponding Source Code Form available as the license requires.
A Larger Work can still contain separate files under different terms: a new file containing no
covered code does not become a Modification merely by being compiled or bundled with the work.

Private use and modification require no publication. Network serving alone is not distribution
of server code, although client code actually delivered raises its own distribution question.
Local sovereignty also needs architectural support: local-first operation, portable custody, and
replaceable composition must make the legal freedom usable.

## The boundary of the Pact

The project may use mythic names for ownership, but MPL follows covered source—not anatomy.

| Material | Result |
| --- | --- |
| LychD source containing covered code | MPL-2.0 governs it. |
| A modified covered file, when distributed | Its modification is MPL-2.0 to recipients. |
| Separate extension with no covered code | It may use other terms. |
| File copying or incorporating covered code | It is a Modification regardless of name or directory. |
| Phylactery data, secrets, configuration, prompts, and model artifacts containing no code | Not covered merely because LychD stores or processes them. |
| A2A or REST peer | Protocol use alone neither copies nor distributes covered server source. |

Independent implementations of an architecture or protocol remain possible because MPL does
not make abstract ideas proprietary. Copying covered expression is a different act, governed by
the license. Calling copied core code an Extension does not change that boundary.

## Receiving third-party material

Upstream rights and obligations survive incorporation into LychD. The project's MPL declaration
neither grants missing reuse rights nor removes obligations on third-party code, tests,
documentation, fixtures or assets. Admission identifies the exact revision and material, its
applicable terms and exceptions, the local use and distribution boundary, and the notices and
source obligations that must travel with it. A public repository or an automated rewrite
supplies no missing permission.

Review distinguishes a dependency or service integration, copied or adapted expression, and an
independent implementation of an idea. Renaming, translation or model assistance does not by
itself establish independence. Unclear provenance or incompatible obligations block incorporation
until resolved; a maintainer's approval cannot waive third-party obligations without the relevant
rightsholder's authorization. GPL/AGPL, custom and source-available terms require a concrete
combination and deployment review rather than an
assumption that they fit an MPL-only distribution.

Prefer a central source-to-destination record and shipped license/notice material. Preserve
inherited notices and satisfy any requirement for notices in the changed files themselves;
central records and Git history cannot replace those duties. README acknowledgements are an
editorial choice, not a licensing condition or a complete legal inventory.

[Assimilation](35-assimilation.md#candidate-author-and-admission) owns the candidate's provenance
contract; [the reuse procedure](../sepulcher/extensions/smith.md#upstream-reuse-and-notices)
shows how contributors retain it. [Packaging](17-packaging.md) owns distribution evidence.

## Contribution terms

Contributions are inbound under MPL-2.0 and distributed outbound under MPL-2.0. There is no CLA,
no relicensing grant, and presently no DCO or required `Signed-off-by` trailer. Any future DCO
must add its certification, instructions, and enforcement together.

Contributors must identify incorporated third-party material and preserve its applicable terms;
the contribution rule grants no rights over upstream material they cannot license.

The repository does not use MPL Exhibit B. Secondary License compatibility is therefore available
under MPL section 3.3 unless a later Covenant deliberately changes that position.

## Consequences

The Iron Pact keeps distributed changes to covered files open while leaving separate code and
private material to their proper owners. To resist cloud capture, LychD must also provide a body
that can run locally, preserve its state, expose provenance, and be left. The license cannot do
that architectural work alone.
