---
title: 0. License
icon: material/link-variant
---

# :material-link-variant: 0. License

## Context

LychD needs reciprocity for the shared core without claiming ownership of every private organ an
operator composes around it. This Covenant calls MPL-2.0 **the Iron Pact**. Its binding text is
the repository [LICENSE](https://github.com/hexanomicon/lychd/blob/main/LICENSE); this ADR records
the boundary and does not amend that license.

## Requirements

- Distributed modifications to covered core files remain open to their recipients.
- Separate, non-covered files can carry their own terms; private use, including intra-organization
  use, does not require publication.
- The project remains OSI-approved and contributions enter and leave on the same terms.
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

LychD is licensed under MPL-2.0.

MPL follows covered source at the file boundary. A distributed Source Code Form containing Covered
Software, including a Modification, stays MPL-2.0. Distribution of an executable containing
Covered Software requires the corresponding Source Code Form to be available as the license
requires. A Larger Work may contain separate files under different terms. A new file that contains
no covered code is not a Modification merely because it is compiled or bundled with the work.

Private use and modification need no publication. Network serving alone is not distribution of
server code; client code actually delivered is a separate distribution question. These legal
boundaries do not create local sovereignty: local-first operation, portable custody, and
replaceable composition must carry that architectural work.

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

MPL does not make abstract ideas proprietary. Copying covered expression remains governed by the
license; independently implementing an architecture or protocol is a different act. Naming copied
core code an Extension creates no loophole.

## Contribution terms

Contributions are inbound under MPL-2.0 and distributed outbound under MPL-2.0. There is no CLA,
no relicensing grant, and presently no DCO or required `Signed-off-by` trailer. Any future DCO
must add its certification, instructions, and enforcement together.

The repository does not use MPL Exhibit B. Secondary License compatibility is therefore available
under MPL section 3.3 unless a later Covenant deliberately changes that position.

## Consequences

The Iron Pact keeps distributed changes to covered files open and leaves separate code and private
material to their proper owners. It cannot prevent cloud capture by license alone; that resistance
depends on a body that can run locally, preserve its state, expose provenance, and be left.
