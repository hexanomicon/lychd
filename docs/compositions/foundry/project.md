---
title: Project
icon: material/source-branch
---

# :material-source-branch: Project

A project binds the design, repository revision, engine and adapter versions, dependencies,
environment, build recipe, declared scenario, and acceptance checks before work begins.

`game.bootstrap_project@1` creates that custody boundary. `game.build_playable_slice@1` then changes
only the feature named by the Invocation and preserves the source diff that produced it. Project
truth includes scenes, resources, settings, tests, and design decisions; engine-native imports and
rebuildable caches remain separate records.

A passing model explanation, attractive screenshot, or generated source tree is not a game. The
project must still load under its pinned engine, satisfy deterministic checks, build, and survive
the declared playtest scenario.

License acceptance and destructive source changes are separate gates. Restart resolves the pinned
Pattern, source, engine, adapter, environment, and schema. Incompatible parked work drains,
migrates through an explicit adapter, or ends honestly rather than moving to “latest.”

Continue with [Assets](assets.md), [Playtest](playtest.md), or [Build](build.md).
