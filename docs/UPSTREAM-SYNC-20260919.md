# CMaNGOS playerbots updates for native Turtle

Integrated locally through `4120aa9d3abf0afc1836f6ba90596c978b1161f5` from `cmangos/playerbots` master, after the previous `266268c6` sync. No branch, commit, production change or server binary was created.

## Updates included

- `7bcee961`: cached unit targets now store GUIDs. Actions and triggers resolve the live unit when used. All additional ManTech combat/encounter callers were migrated too.
- `b36cec53`: conditional fishing compilation fix retained (Wrath-only part is not exercised by Turtle).
- `a541d244`: `cdebug why` explains current behavior.
- `f299b8ba`: statistics return text to remote administration as well as in-game callers.
- `fe6f4b31`: `.rndbot sample` and `.rndbot find` show bots matching behavior filters.
- `1ae52c41`: `cdebug engine` shows recent trigger/action decisions.
- `d685f18f`: `cdebug history`, `.rndbot history`, and optional `AiPlayerbot.ActionHistorySize` (default **0/off**).
- `53ebb2d4`: cross-map mutation safety adapted to Turtle's existing bounded WorldActions queue. Summon, custom-cast and world-buff apply actions require world-owner execution. Preserve native explicit summon/revival, including taxi/charm cleanup, instead of importing CMaNGOS packet/resurrection APIs. Arena gathering and random group relocation already run on the world owner; preserve the native filters and teleport result checks.
- `7f23556e`: check map identity before querying underwater movement height.
- `4120aa9d`: donor resurrection compilation follow-up reviewed; its API is not used because Turtle keeps its native revival path.

## Preserved behavior

Our healing urgency, personal DoTs, crowd-control protection, WSG objectives, summon handling, target visibility checks, mailbox correction, and aura/allocation memory fixes remain. Statistics use module-slot lookup and Turtle area names. Live statistics remain on the world owner, with no detached stats thread.

GUID migration supersedes our older cached-pointer-plus-GUID adapter. Initial calculations still run immediately, including zero-interval values. Manual target Reset/LazyGet still dispatch through the current/pull target overrides. A GUID can remain cached after removal, but consumers resolve it against live native objects before use.

## Validation and next step

- Compiler syntax checks passed for 104 changed translation units and 11 class contexts/factory files; no server linking performed.
- Extracted production GUID cache and current-target tests passed: expiry, removed objects, first calculation, visibility/range, reset and lazy access.
- Extracted native cross-map dispatcher tests passed: world/same-map execution, deferred foreign-map execution, removed/teleporting target and queue rejection.
- Existing actual healing-selection tests passed in Classic/TBC/Wrath fixture modes.
- Existing allocation-churn regression passed, preserving the auction and travel memory corrections.

Run **Build-Local-Turtle**, then deploy/test as usual. No database migration is required. Full linking, in-game diagnostics, live summons and runtime load have not been tested by this update.
