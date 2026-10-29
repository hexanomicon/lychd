---
title: Assets
icon: material/image-multiple-outline
---

# :material-image-multiple-outline: Assets

A sprite, texture, illustration, or model begins as a candidate. Its attractive surface is only one part of the decision: Atelier must also retain what influenced it, which transformations made it, and whether it meets the declared role.

## Candidate lineage

`atelier.forge_concept_set@1`, `atelier.forge_sprite_set@1`, `atelier.forge_texture_set@1`, and `atelier.forge_model_asset@1` combine admitted generation, procedural work, deterministic transforms, manual editing, capture, or authored sources.

Keep the candidate's source references, classifications, permitted influence, and retention together. Its production record names the tool/provider revision, prompts or controls, seed when available, cost, and result.

The production history must let a reviewer follow each candidate back through its changes. Each transform therefore binds its parent digest, operation, parameters, implementation, output digest, and loss. Review adds the asset revision, role, format/profile facts, findings, approval, and derivatives. Both generation and normalization create artifacts with parents.

Spatial candidates additionally declare geometry, appearance, structure, deformation, assembly and procedural facets; units, axes, origin, scale, bounds and transforms; material channels, parts, skeleton and camera facts; and representation conversions. A glTF/GLB can contain mesh, PBR appearance, skeleton, skinning and animation together. Point clouds, Gaussian and radiance forms, neutral voxels, game block grids, and portable assemblies remain distinct forms. [Prism Form](../../sepulcher/extensions/prism/form.md) owns their technical production; Atelier owns visual acceptance.

## Produce, normalize, review

Make the candidate against the exact brief and direction. Before decoding its media, apply the hostile-media limits in [Vision](../../adr/36-vision.md). Then establish whether the result can meet the target: probe format, dimensions, frames, color, geometry, topology, materials, units, axes, bounds, size, and any other target limits. Retopology, baking, rigging, voxelization, and other normalization preserve lineage and declared loss. They may repair technical fit; an ambiguous likeness or failed source still needs its own resolution.

Review selects, rejects, or returns attributed findings. The smallest supported repair creates a new candidate; accepted material is replaced only by a successor revision. Unresolved influence, consent, likeness, Portal egress, or target fit produces quarantine, reduced scope, or refusal.

Paid generation binds idempotency identity and exact request digest. A lost acknowledgement leaves it **unknown** until provider records reconcile it; another attempt could buy the same work twice.

Accepted revisions enter [Package](package.md); temporal work continues through [Motion](motion.md). Neither result carries engine, editorial, or publication authority.
