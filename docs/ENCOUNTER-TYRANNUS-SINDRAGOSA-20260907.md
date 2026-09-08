# Encounter audit continuation: Tyrannus and Sindragosa

Development work after Playerbots baseline `784d2c2e`. No production deployment
or persistent database writes are part of this continuation.

## Implemented

- Tyrannus Overlord's Brand (69172): native aura proc routing copies the marked
  player's outgoing damage to the boss's current victim, and outgoing healing
  to Tyrannus at 5.5 times its amount. Both direct and periodic events use the
  native proc pipeline. Taken damage/healing, zero amounts, recursive payloads,
  dead/missing casters and other instances/phases are rejected. Integer payloads
  are bounded. Migration 5879 supplies the previously missing script/proc rows.
- Branded bots stop their own attacks and interrupt harmful/healing casts;
  dispels, shields and ordinary buffs remain available. The hold ends with the
  aura/encounter. Unbranded pets and other party members continue acting. Existing
  periodic effects and already launched projectiles are not erased.
- Rimefang receives Mark of Rimefang only after the native hit has applied its
  aura. Hoarfrost retries a rejected cast while the marked target is valid, and
  cancels when the target, aura or encounter expires. Reset clears the cached GUID.
- Icy Blast used a corpse-only despawn timer for a passive living actor. Its
  lifetime now follows the native ground spell duration with timed despawn;
  invalid/missing duration data cannot create an immortal actor.
- Sindragosa phase three now casts the explicit single-target selector 69675
  instead of the air-phase area selector 69712.
- A rejected air-phase tomb selector remains pending. The cover/bomb phase
  timers begin only after the selector cast is accepted.

## Evidence and verification

The native Tyrannus source explicitly marked Brand unimplemented. Read-only dev
queries found no 69172 script or proc row. Existing payloads 69189/69190 supply
the damage/healing effects. The 5.5 healing multiplier and destination behavior
are corroborated by the [AzerothCore native Brand implementation](https://github.com/azerothcore/azerothcore-wotlk/blob/master/src/server/scripts/Spells/spell_generic.cpp).
This comparison is implementation evidence, not a claim of measured live retail fidelity.

Four regression runners execute six C++ fixtures: native Brand/Rimefang,
native spell-proc admission/Icy Blast lifetime, damage-pause policy in each
expansion, and Sindragosa phase boundaries. They passed. The single incremental
Wrath native build also passed; EXE/PDB identity matched. Full prior suites were
not repeated. Migration 5879 applied twice to session-local temporary tables
with exactly one binding/proc row; persistent tables remained unchanged.

## Findings still open

- Sindragosa is not fully implemented by these selector corrections. Local
  70126 references absent 70159; 70157 has no trap handler, 36980 and its difficulty
  templates have no actor AI, and the relevant spell bindings are absent. The
  Ice Block gameobject 201722 does exist (door type, display 9244), correcting
  the narrower earlier query that searched only names containing "Ice Tomb".
  Tomb creation, trapped-player protection/release, asphyxiation, owned object
  cleanup, attack access to the tomb and Frost Bomb/Mystic Buffet cover need
  integrated native implementation and real map validation. Ordinary gameobject
  collision support exists; the whole core does not lack dynamic LOS support.
- Sindragosa 69846 is also a dummy without a binding in the inspected dev data;
  its intended Frost Bomb actor 37186 does have `mob_frost_bomb`. The damage spell
  69845 is caster-centred, while the current marker AI asks Sindragosa to cast it.
  Complete the marker creation/origin/cover chain together before enabling it;
  restoring room-wide bomb damage without functioning cover would be unsafe.
- Lich King's native script remains at its recorded incomplete state: initial
  phase/reset handling, transition initialization, heroic Shadow Trap cleanup,
  platform destruction, ending/cinematic and Frostmourne-room work are still
  explicitly unfinished. This is larger than an isolated bot targeting change.
- Emalon uses EventAI, including a distinct 25-player 65279 Nova. That spell has
  a 100-yard radius and no local script binding. An [AzerothCore native reference](https://github.com/azerothcore/azerothcore-wotlk/blob/master/src/server/scripts/Northrend/VaultOfArchavon/boss_emalon.cpp)
  implements distance falloff reaching zero at 70 yards. This makes the radius
  alone insufficient evidence for changing it to 20 yards. Native damage intent
  and the bot planner's 35-yard limit remain unresolved; no radius was invented.

Full encounter role assignments, integrated normal/heroic runs and server-load
measurements remain separate outstanding coverage. No whole-audit completion
or numerical performance improvement is claimed.
