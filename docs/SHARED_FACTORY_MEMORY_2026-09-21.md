# Shared registration tables for CMaNGOS

Ported the opt-in registration-table sharing used by ManTech Turtle to the shared Classic, TBC and Wrath Playerbots source. Twelve common contexts and 118 class-specific contexts now share immutable creator registrations. Concrete context types keep separate static tables. Created objects, actor state, qualifiers, caches, recursive mutexes, reset/erase behavior and local registration overrides remain per-context.

The port preserves the local CMaNGOS registrations rather than replacing context files with Turtle versions. A comparison with pre-port snapshots confirmed that all 130 constructor token streams are unchanged after removing the sharing wrappers. Registrations use actor-independent creators. Runtime/class-dependent factories remain unchanged unless explicitly opted in.

Validation: `tests/shared_factory_regression.py` compiles the production factory/context templates with controlled interfaces. It covers concurrent first initialization, actor isolation, qualifier handling, unsupported keys, reset/erase, overrides, distinct concrete types/namespaces and exception retry. The 200-context/1,500-registration fixture allocated 47,400,000 bytes without sharing versus 40,000 after shared initialization. These are allocation-fixture results, not measured production savings or proof that long-run memory growth is resolved.

Related pending baseline changes published with this port include party combat support, tank rescue priorities, dungeon healer/BRD target choices, safer fleeing-target pursuit and leader-follow jumps, and distinct unavailable-versus-failed action diagnostics. Healer-support, movement-dispatch and threat tests pass in Classic/TBC/Wrath modes; target-selection source checks pass. Stale fixtures were updated for the existing ObjectGuid APIs.

Published as source-only at the user's request. No new game binaries, production deployment or database changes were performed. Core warning SQL is stored in each core's `sql/custom/world` directory; this memory optimization itself needs no SQL. Full builds and in-game verification remain for the user's next planned release.
