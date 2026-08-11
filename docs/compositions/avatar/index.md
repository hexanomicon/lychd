---
title: Avatar
icon: material/account-outline
---

# :material-account-outline: Avatar

Avatar is the Composition that assembles and governs one Lich presentation across one or many
separately admitted projections. Spectre is the VR Composition whose Habitat may admit one of those
projections; meeting the Lich through it is a bounded Spectre Encounter. Neither Composition
absorbs the other: Avatar settles presentation and projection membership, while Spectre settles
the VR Habitat, Encounter, comfort, interruption, and safe exit.

The Lich may appear at once through an Avatar projection inside a Spectre VR Habitat, a Blockworld
inhabitant, a room display, and a simulated physical body without turning any character, device,
provider session, or encounter into its identity. Every target retains its own truth, authority,
and right to refuse.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `avatar.presence` revision `1` |
| **Patterns** | `avatar.compose_profile@1`, `avatar.bind_morphe@1`, and `avatar.project_presence@1` |
| **Application begins with** | for profile composition, an exact eligible Persona revision plus exact visual, voice, motion, language, disclosure, and fallback references; for a Morphe, one immutable profile plus exact eligible presentation, target, audience, timing, disclosure, and fallback references; for presence projection, one immutable profile plus admitted participant and target references, exact target capability snapshots, synchronization policy, consent, privacy, budgets, and stop conditions |
| **Application can return** | an immutable `AvatarProfile@1`, admitted `MorpheBinding@1`, settled `AvatarPresence@1`, per-target `ProjectionBinding@1` records and receipts, or explicit partial/non-completion |
| **Application stops before** | creating identity, changing Persona commitments or memory, opening an unbounded ambient presence, owning a target world or device, claiming unobserved delivery or motion, or granting physical and virtual effects |

Avatar owns the assembled presentation profile, allowed Morphe, projection membership and epochs,
semantic synchronization policy, per-projection admission and lifecycle references, degradation and
fallback judgment, and aggregate settlement. It does not own the Lich, Persona, Context, raw media,
source assets, provider sessions, target-world state, locomotion, manipulation, or consequential
effects.

## Records, selection, and projection epochs

Avatar keeps four layers separate so that changing a form, losing one target, or ending one
meeting never rewrites identity or invents continuity elsewhere.

| Record | Avatar-owned truth | Boundary |
| --- | --- | --- |
| `AvatarProfile@1` | one immutable Persona revision plus the eligible visual, voice, motion, language, disclosure, provenance, licence, and fallback envelope | eligibility and defaults, not one live body, target, session, or claim that every eligible facet was rendered |
| `MorpheBinding@1` | one immutable selection from that envelope for an audience, target class, purpose, time window, and disclosure posture | presentation selection inside one Persona boundary, not a mutation of the profile or a second identity |
| `AvatarPresence@1` | one declared multi-projection purpose, required and optional members, synchronization mode, aggregate ceilings, and settlement policy | correlation of projections, not shared Context, indivisible attention, or target authority |
| `ProjectionBinding@1` | one independently admitted target epoch pinning the profile, optional Morphe, target and capability receipt, participants, consent, disclosure, fallback, stop conditions, and attributed terminal result | membership in the Avatar presence, not ownership of the target's world, device, Invocation, provider session, or effects |

The profile is therefore an **eligible presentation envelope**. A Morphe is one pinned selection
inside it. Opening a projection never means copying the Persona, and changing a Morphe does not
edit an open or historical binding. A changed form, target epoch, capability set, participant
scope, consent grant, or disclosure posture either opens a newly admitted `ProjectionBinding@1`
or closes the affected binding according to its declared fallback.

Revocation follows the same rule. If an asset licence, performer consent, audience permission, or
target capability is withdrawn, Avatar does not silently substitute a similar face, voice, motion,
or body. It closes the affected projection or admits a new compatible binding whose changed
sources and disclosure are explicit. Earlier records remain immutable and attributable.

Each target opens and settles its own local work. A Spectre Encounter, Blockworld mission, Reach
turn, room display, or embodied controller may receive the same attributed semantic act, but each
retains a distinct Context, authority, chronology, observation, and result. Avatar correlates the
bindings named by `AvatarPresence@1`; it never turns them into one universal session or proof of
one continuous field of attention.

## One Lich, many projections

`AvatarProfile@1` binds exact eligible visual, voice, motion, language, disclosure, and fallback
references without copying their source truth. `AvatarPresence@1` binds one exact profile and
Persona revision to any number of independently admitted `ProjectionBinding@1` records.

A presence may use two closed modes:

- **mirrored** — one attributed semantic act is requested across several projections, with a
  separate delivery or effect receipt from each target;
- **parallel** — each projection opens its own bounded Invocation with the same Persona revision
  but distinct Context, authority, outcome, and attribution.

Parallel projections do not prove one indivisible field of attention. A projection may join,
degrade, refuse, disconnect, or finish without inventing the state of another. Global completion
means only that the declared aggregate policy has settled every member honestly.

| Aggregate result | Meaning |
| --- | --- |
| **completed** | every required binding returned an eligible attributed terminal result |
| **partial** | the declared policy permits the exact settled subset and names every absent, refused, interrupted, or still-running member |
| **refused** | the presence or one policy-required binding failed admission before it could begin |
| **unresolved** | a required target outcome remains unknown or cannot be reconciled without guessing |

## Morphe changes presentation, not identity

**Morphe** is an admitted change of voice, appearance, animation, manner, language, or disclosure
inside the same Avatar profile and Persona boundary. A `MorpheBinding@1` pins the selected assets,
target compatibility, audience, timing, disclosure, and fallback. A cat, stylized game character,
or performer-inspired presentation may be a Morphe of the same Lich; it may not claim separate
memory, commitments, relationships, authority, or personhood.

If the requested change crosses those identity boundaries, Avatar refuses it and Mirror requires
an explicit Persona revision or a distinct Persona. Resemblance never grants performer authority;
voice and likeness use retain their own consent, licence, provenance, disclosure, and revocation.

## Representative journey: one Avatar in VR and Blockworld

1. The Magus composes one immutable `AvatarProfile@1` from an exact Persona revision and admitted
   visual, voice, motion, disclosure, provenance, licence, and fallback references, then admits one
   target-scoped `MorpheBinding@1` from that eligible envelope.
2. A Spectre VR Habitat and a Blockworld mission are admitted independently. Avatar opens one
   `AvatarPresence@1` declaring which projections are required, whether their semantic acts are
   mirrored or parallel, and how partial settlement is judged. It opens a separate
   `ProjectionBinding@1` epoch for each target.
3. A participant enters the VR Habitat and meets the Lich's Avatar, opening one Spectre Encounter.
   Spectre retains Habitat capability, comfort, interruption, and exit truth; Blockworld retains
   its world epoch, mission, inventory, and effects.
4. One attributed greeting may be mirrored across both projections, but each target returns its
   own delivery or effect receipt. Neither result proves the other occurred.
5. The XR runtime is lost. Spectre records an interruption and settles or explicitly offers
   recovery; Avatar settles that VR binding epoch only from Spectre's attributed result. The
   Blockworld binding and mission may continue because no VR event grants or removes world
   authority.
6. If recovery is accepted, Spectre re-admits capabilities and Avatar opens a fresh VR binding
   epoch under the recovered facts. If recovery is refused, the VR member remains interrupted.
   Avatar waits for or stops the Blockworld member according to the declared aggregate policy, then
   reports the presence as completed, partial, refused, or unresolved without inventing shared
   target state or uninterrupted embodiment.

## Target truth stays local

| Target | Authority retained outside Avatar |
| --- | --- |
| [Reach](../reach/index.md) | social event, Habitat audience, platform delivery, and reply receipt |
| [Blockworld](../blockworld/index.md) | world epoch, inhabitant, mission, inventory, lease, and verified world effect |
| [Spectre](../spectre/index.md) | VR Habitat admission, Encounter chronology, comfort, interruption, and safe exit |
| room or household display | Homestead place policy, bystanders, capture indicators, device purpose, and local controls |
| vehicle | the selected vehicle controller's occupants, safety envelope, device purpose, local controls, and motion or effect authority |
| drone or robot | Legion node identity, controller health, physical envelope, emergency stop, and effect receipt |

Prism and Voidlight retain visual artifact truth, Echo and Riffmaw retain audio and voice truth,
Kinesis retains technical motion, and Mirror retains Persona identity. Avatar assembles exact
eligible references and decides only whether the resulting projection profile is coherent for the
declared presence and target capabilities.

### A VR projection is not embodiment

For Spectre, Avatar consumes the exact admitted Habitat capability result and opens a binding
whose target is that `VRHabitat@1`. Avatar may select eligible head, hands, body, voice, motion,
caption, disclosure, and fallback facets, but it does not create the XR session, choose or own the
runtime reference space, grant locomotion or haptics, capture tracking, or decide Encounter entry
and exit.

Head, hand, gaze, face, or body tracking is target input. Its availability may constrain the
Morphe and projection, but a tracked signal never proves Persona identity, participant intent,
attention, emotion, consent, physical co-location, or remembered experience. Raw high-rate input
stays with the admitted engine/runtime path. Avatar keeps only the capability facts and attributed
semantic results needed to settle its binding.

If the XR runtime is lost and Spectre later admits recovery, Avatar closes or explicitly links the
old projection epoch and admits a fresh one under the recovered Habitat facts. It never fabricates
an uninterrupted embodiment merely because the same profile appears again.

## Core capability before packaging

Avatar belongs in the Portfolio without requiring a current packaged application. A later
**Avatar Studio** may package customization and preview; a Suite may combine Avatar with Spectre,
Blockworld, Reach, or a physical embodiment. Neither packaging choice moves target authority into
Avatar.

The smallest proving fixture is synthetic and network-disabled: one profile projected
simultaneously into a mock text-and-voice surface, Blockworld adapter, Spectre adapter, and physical
body adapter. It proves mirrored and parallel modes, one-target refusal, capability downgrade,
Morphe change, disconnect, restart, consent revocation, partial settlement, export, and deletion.
No public platform, real performer clone, headset, drone, vehicle, or robot enters that fixture.

Related: [Identity](../../adr/32-identity.md) · [Vision](../../adr/36-vision.md) ·
[Audio](../../adr/37-audio.md) · [Composition Portfolio](../index.md)
