# Bot reliability experiments

These adaptations are opt-in and default off in all three configuration templates.
They reuse CMaNGOS movement, spell, group and portal handlers. They are not a port
of Tortoise's core, session scheduler or private analytics service.

| Switch under `AiPlayerbot.Reliability.` | Behavior |
|---|---|
| `UnreachableTargets` | An NPC outside LOS, with no useful progress for 15 seconds, is excluded for 30 seconds. Progress, LOS, explicit targets, group combat and map transitions reset or override the decision. Eight exclusions maximum per bot. |
| `DungeonCorpse` | A ghost outside its corpse's dungeon approaches the native entrance and uses the normal area-trigger handler. No forced resurrection or entry bypass. Existing autonomous long-death fallback remains. |
| `BodyPull` | Explicit `pull` / `pull rti` may approach for native melee when the configured ranged pull lacks equipment, ammunition or training. Automatic pulling, cooldown failures and LOS failures do not enable this fallback. Existing deadline and pull-back behavior remain. |
| `PartyCommands` | `party interrupt`, `party cc`, and `party pull` in party/raid chat select one available owned group bot. The target is captured on receipt. Each bot checks its own readiness in its map update. A shared reservation prevents duplicate execution. The selector prefers tanks briefly for pulling; individual pull commands remain available. |
| `IncidentHistory` | Samples movement/death and records repeated action failures and unreachable-target episodes. No recovery behavior is triggered by these observations. |

The command coordinator uses the normal cast/pull checks. Interrupt candidates are
kick, pummel, shield bash, counterspell, silence, plus earth shock in Classic/TBC
or wind shear and mind freeze in Wrath. CC candidates are polymorph, shackle,
hibernate and banish. It does not introduce fear pulls or ground-targeted traps.
An accepted message means the cast/pull started, not that the spell landed.

## Incident storage and overhead

Incidents are keyed by run, bot, kind and monotonic start time. Death must persist
five minutes, movement without progress thirty seconds, and repeated failure
fifteen seconds before an episode opens. Recovery and observation expiry are
different statuses. Action names and unreachable target GUIDs accompany records.
These are clues for investigation, not proof that a particular action is defective.

State is lazy and bounded per bot; the write queue holds at most 4,096 records.
Only transitions enter that queue, not every tick. The manager flushes at most
once per ten seconds. `PlayerbotIncidents.jsonl` rotates at 16 MiB with one prior
generation (plus one bounded flush). Data persists in those files across restart;
active episode state does not. Records lost to capacity are counted. Turning the
switch off bypasses sampling. No realm RAM cap is introduced.

`tools/dev-incidents/bot-incidents.php` is a read-only, loopback-only viewer for
the existing local Classic/TBC/Wrath candidate directories. It reads bounded tails
and never accepts a filesystem path from a request. This is DEV tooling; it must
not be copied to the public production website as-is.

## Validation before promotion

Build all three cores with the pinned module and retain the account membership,
map lifecycle, and hotpath source overlays. Run the focused pursuit, command,
pull and incident tests plus each core's existing CTests. Test native gameplay in
DEV: a wall/unreachable target that is not attacking the party; normal group
combat and a boss; a released dungeon ghost; an equipped pull followed by a
no-ammo explicit pull; two eligible interrupters receiving one party command.
Observe episode counts and memory/tick cost at the configured bot population.
Compilation and policy tests alone do not establish native pathfinding or raid
behavior. Production promotion is a separate step after those checks.

## Origin and deliberately retained differences

The candidates came from Sagiroth/TortoiseBots: unreachable pursuit in PR 157,
dungeon recovery in PR 172, pulling improvements in PR 167, its party command
coordinator, and the observability episode tracker. These are independently
adapted to the existing ManTech APIs. Existing pull-back, logout-stun fixes,
safe path handling, role helpers and gated profiling were already present.
Tortoise-specific runtime rescue and shared target-scan throttling are excluded:
they have different core/scheduler assumptions and are not safe drop-in changes.

## Diagnostics removal inventory

New removable observation components: `BotIncidentHistory.*`, the `incidents`
member in `BotReliabilityState`, the sample hook in `PlayerbotAI::UpdateAI`, result
hooks in `Engine`, the unreachable observation call, the manager flush hook,
the `IncidentHistory` config entry and the DEV PHP viewer. These can be disabled
with one config switch independently of the four behavioral experiments.
