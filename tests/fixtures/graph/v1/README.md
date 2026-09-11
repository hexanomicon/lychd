# Pydantic Graph 1.107.5 checkpoint receipts

These inert fixtures were captured before the upgrade from the real LychD
`perform_run` consent/delegation path and `GraphRunner` hardware-retry path. They
contain only generated test identities, the approval test tool, and the inert
reference delegate. No real provider, process, database, or hardware effect ran.

`consent-pending.json` records the same real park after `load_next` committed its
pending status. It remains decodable but is not automatically replayable.
`hardware-budget.json` records one hardware retry followed by a consent park.
The declared fixture node is inert in codec tests; only its retained shape is used.

These fixtures prove supported old-wire decoding and bounded continuation. They
do not prove a process restart, migration of database schema, or broker recovery.
