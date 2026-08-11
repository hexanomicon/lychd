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
   visual, voice, and motion references.
2. A Spectre VR Habitat and a Blockworld mission are admitted independently. Avatar opens one
   presence with a separate projection binding for each target.
3. A participant enters the VR Habitat and meets the Lich's Avatar, opening one Spectre Encounter.
   Spectre retains Habitat capability, comfort, interruption, and exit truth; Blockworld retains
   its world epoch, mission, inventory, and effects.
4. One attributed greeting may be mirrored across both projections, but each target returns its
   own delivery or effect receipt. Neither result proves the other occurred.
5. The participant exits VR, so Spectre settles the Encounter. Avatar separately settles the exact
   `ProjectionBinding@1` from Spectre's attributed exit result; the Blockworld binding may continue
   until its own Invocation settles. Avatar then reports the declared aggregate presence as
   complete, partial, refused, or unresolved without inventing a shared target state.

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
