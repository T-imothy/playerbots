# Disabled AI telemetry overhead

Adapted from Sagiroth/TortoiseBots issue 175, PR 177 (head
03f96a68fb356f3459261fcb8eda9546d0a46a2c), reviewed 2026-09-15:
https://github.com/Sagiroth/TortoiseBots/pull/177

UpdateAI, UpdateAIReaction and UpdateAIInternal previously constructed a
WorldPosition and profiling label before PerformanceMonitor::start rejected
disabled profiling. All three now check perfMonEnabled before doing that work.
Enabled profiling retains its labels, scope and explicit operation reset points.
This is shared by Classic, TBC and Wrath. No config or database migration is needed.

The other upstream changes are not carried into this release:

- SyncNativePlayers and SweepStrandedBots belong to the Tortoise runtime and do
  not exist in this CMaNGOS runtime. Our player membership is updated on lifecycle
  events rather than rebuilding Tortoise's compatibility view each world tick.
- Our RandomPlayerbotMgr::OnPlayerLogin excludes free random bots from GetPlayers.
  Owned/non-random bots can be present. Replacing it with a global session walk
  would change existing friendship semantics and requires a separate threading
  review; it does not remove the same all-random-bot scan described upstream.
- PR 178 is closed without merge at review time. PossibleTargetsValue here already
  inherits NearestUnitsValue's cached interval. Its proposed early idle return
  precedes the combat safety checks, and its scan timestamp is shared across
  qualified values. Importing it would change target discovery behavior and is
  not part of this overhead-only fix.

Run tests/disabled_telemetry_regression.py under a Visual Studio developer shell.
It compiles the actual entry blocks for all three expansion defines, verifies
zero collaborator calls while disabled, and verifies enabled labels and lifetime,
including a monitor with no available map entry. Full core builds and existing
CTest suites remain release gates. No production percentage improvement has
been measured or promised; this removes a specific unnecessary cost.
