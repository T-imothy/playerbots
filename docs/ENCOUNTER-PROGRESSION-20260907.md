# Encounter progression continuation

The resumed development audit adds the following behavior. The complete
raid/dungeon mechanic register remains open; these are specific implemented
rules, not claims of complete encounters or live raid clears.

| Encounter | Implemented behavior | Scope |
| --- | --- | --- |
| Twin Emperors | Caster DPS prefers Vek'lor; physical DPS, including hunters, prefers Vek'nilash. Selection waits for a live group victim after teleport and preserves explicit targets, tanks, healers and crowd control. | All three cores |
| Syth | DPS prioritizes the boss's four elemental entries. Native health thresholds retain successful elemental summons and retry failed ones without duplicating a partial wave. Reset clears all three wave masks. | TBC/Wrath |
| Maladaar | DPS prioritizes native souls and the avatar. Souls require a group player as summoner and spell 32360; the avatar requires the boss as summoner. The ownership mode is rechecked for each candidate. | TBC/Wrath |
| Telestra | DPS selects native clones only during split aura 47710. The native one-shot merge timer retries a failed cast every 500 ms while the completed split remains active; normal and heroic splits share the lifecycle checks. | Wrath |
| Eadric | Normal/heroic Radiance damage and stun check the victim's facing. Bots turn away during warning cast 66935; automatic target-facing and competing combat actions preserve that turn. Safe stationary friendly spells and emergency ground-hazard movement remain available. | Wrath |

The Syth targets retain native school immunities. This continuation does not
add specialization-aware elemental assignments. Twin Emperors tank assignments,
room routes and recovery from crossed tanks also remain outside the implemented
DPS selection. Telestra's new retry is a failed-cast recovery; duplicate clone
death events were not established as a native defect.

Eadric's previous local spell bindings were empty for both 66862 and 67681.
Spell metadata and generic targeting supplied no facing restriction. The
independent [TrinityCore implementation](https://github.com/TrinityCore/TrinityCore/blob/3.3.5/src/server/scripts/Northrend/CrusadersColiseum/TrialOfTheChampion/boss_argent_challenge.cpp)
also filters both damage and stun using the target's facing, with a 2.5-radian
arc. The implementation here uses the CMaNGOS spell-script target hook and
retains the native spell radius, damage and stun duration.

Wrath migration `Updates/5877_eadric_radiance_facing.sql` binds the two payload
spells to `spell_eadric_radiance`. It is required with the new core behavior.
Actual local-schema tests verified insertion, repeat application and rollback.
Bindings were loaded for the isolated Wrath runtime check, then removed before
restoring its original development executable. Production databases were not
changed. Earlier audit migrations remain separate requirements.

## Validation checkpoint

- Full regression suite: 127/127 runners passed, including actual-method tests
  for target ownership, role/manual controls, partial-wave failures, both merge
  phases, facing geometry, safe heals and reaction/automatic-facing wiring.
- Windows x64 RelWithDebInfo `mangosd` builds passed for Classic, TBC and Wrath.
- Isolated local startup: Classic 38.14 s, TBC 95.22 s, Wrath 88.23 s. All three
  subsequently exited successfully after graceful shutdown requests; no SQL
  errors or assertions matched the runtime check.
- Diagnostics observed 20 online bots in Classic/TBC and 19 in Wrath, with a
  configured target of 20. These are startup checks, not raid combat or load
  benchmarks. Existing world-data warnings are not certified resolved.
- Existing production Hammer source was applied separately to all three audit
  cores. The queued-owner lifetime and Wrath party-status fixes remain included.
  The original development executables were restored; production files and
  baseline branches were not modified by this continuation.

The worktrees are still uncommitted. Local builds use the local playerbots
source override; the old CMake pin does not identify this dirty checkpoint.
Complete mechanic assignments, vehicles, event progression, difficult room
geometry and live normal/heroic/raid execution remain in the main register.

## SSC ownership and encounter item follow-up

Leotheras's personal demon selection requires the bot's actual Insidious
Whisper aura from live Leotheras 21215, a native player-owned summon 21857
created by 37735, and that demon's current victim being the bot. Other players'
demons are excluded. Explicit attack/raid-icon orders remain authoritative.
This personal objective precedes ordinary healer/tank exclusions; ordinary add
objectives still preserve those role exclusions. Healers receive a normal
learned-rank Smite, Wrath, Lightning Bolt or Exorcism action where available;
native mana, form, cooldown and range checks remain in force. This does not
grant missing spells, force forms or certify every healer configuration.

Native item-use admission now always requires real Hourglass Sand, Tears of
the Goddess, Tainted Cores and Naj'entus Spines even with the item cheat enabled.
Previously their consumable/miscellaneous classes bypassed `itemUsed`, so
possession checks in encounter actions alone did not preserve consumption.
Actual database metadata confirms Sand/Core/Spine have consumable charges -1;
Tears have zero charges and remain reusable under their native cooldown.
The regression reproduces the previous bypass in each era and verifies the
repair without changing ordinary consumable cheat behavior.

Subsequent full suite: 129/129 runners passed. All three subsequent native
builds passed (`build-*-ssc-items.log`). The startup results above precede
these last two source changes; they must not be represented as runtime tests
of the later binaries. These follow-up changes require no additional SQL.

Vashj core relay/generator routing remains under investigation. Native item
31088 has separate throw spell 38134 and opening spell 3366; generator lock
1718 requires item 31088. Item IDs in Lock.dbc must not be interpreted as spell
IDs. No relay implementation or generator-path success is established yet.

The four encounter items now dispatch exactly one verified native on-use spell
through `Player::CastItemUseSpell`. Classic/TBC select the actual item slot;
Wrath selects the spell ID. Core throws require a different player; generator
opening selects 3366 and a game object. Invalid or absent explicit targets do
not become self-casts. Native inventory, charges, cooldowns, locks and cast
rejection remain authoritative. The result means an attempt was dispatched,
not that the effect succeeded. No item pointer is used after native dispatch,
which can consume the item immediately. Ordinary item-use behavior is unchanged.

The three items with empty ScriptName have no separate native item-use hook;
`item_tainted_core` registers a loot hook, preserved by the core's inventory
handling. Native dispatch and actual-method regression fixtures cover all era
APIs, missing/foreign/traded items, alternate item slots, target types, consumed
items and stale world state. This fixes the item-use foundation; it does not
add automatic Vashj looting, relay assignments or generator navigation.

Latest native-item checkpoint: 130/130 regression runners and all three Windows
builds passed. Source/binary fingerprints and validation references are saved
in the task's `checkpoint-native-items.json`. The work remains on the dirty
enhancement branches; no production deployment or baseline promotion occurred.

## Vashj core progression and Striders

Bots now collect the actual core from an eligible native Tainted Elemental corpse,
reserve one free DPS receiver per carrier, and use the real throw/open item slots.
A receiver moves along a validated route; the rooted carrier is never teleported,
unrooted or given replacement items. Handoffs require measurable progress toward
an active generator, native range/LOS, capacity and current safe landing space.
Eight candidate receiver paths are the limit per cached calculation. Native loot
rights, item consumption, cooldown and lock results remain authoritative.

Tanks, healers, current elite/Strider victims and bots following explicit target,
stay, guard or skip-item orders are excluded from collection/receiving. Existing
core holders still deliver. Tainted Elementals take DPS priority, followed by
Enchanted Elementals nearest the boss, then ranged Strider targets and elites.
Strider fear radii come from native spell38258 and feed the shared hazard
path/chase/escape checks. Live source ownership, self-aura38257 and shield phase
checks prevent persistent obstacles after death or phase transition.

The actual-method fixture tests assignment, multiple carriers, progress,
consumption, rejected uses, loot slots, stale recipients, maps, paths and moving
hazard lifecycle in TBC/Wrath, with inactive Classic guards. Four previously
uninvoked Syth/Maladaar/Telestra fixture rows are now included and pass. No new
SQL is required for these Vashj changes. Full live encounter clears, threat
acquisition and real room routing have not been established by these fixtures.
