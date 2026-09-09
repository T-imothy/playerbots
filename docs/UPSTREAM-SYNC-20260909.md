# Upstream synchronization â€” 2026-09-09

Merged CMaNGOS playerbots through `89a4e5aebd6aa41ee87f6e65d89b66fff5c5c7c1` (five incoming commits).

- Retain upstream corpse-position, missing-player diagnostic and faction checks.
- Add the upstream guard against acknowledging a battleground that no longer exists.
- Preserve transition generation invalidation, pending-transition cleanup, source-map movement cleanup, and summon revival after successful acknowledgement.
- Preserve the existing null creature-template check and invalid-corpse-position check; upstream's overlapping checks are already covered more fully.

The focused C++ regression executes the merged acknowledgement body for missing/live battlegrounds, ordinary worldports, near teleports, real-player acknowledgement ownership, and transport movement flags in all three expansion variants. Existing battlemaster diagnostic tests also pass. These controlled tests do not establish live battleground recovery behavior after a cancelled worldport.

No healing, rotations, pulling, WSG tactics, loot policy, or configuration settings are changed by this merge. Native encounter mechanics remain governed by CMaNGOS.

Follow-up review reproduced an upstream missing-faction assertion in all three expansion variants. GuidPosition diagnostics now return a neutral fallback when either faction template is unavailable, before contested-guard, reputation, or fallback-reaction code can dereference it. Valid faction behavior is unchanged. The null-template formatter safeguard is also an upstream PR candidate.
