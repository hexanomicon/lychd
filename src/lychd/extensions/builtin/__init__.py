"""Concrete built-in contribution packages shipped with LychD.

Directory presence is never activation or delivery evidence. Only ids in
``builtin.catalog.BUILTIN_EXTENSIONS`` are selectable, and each selected package must expose a
real ``register(context)`` shim. Aspects describe the body's responsibilities, not a required
source-directory layout or a catalogue of replaceable packages.
"""
