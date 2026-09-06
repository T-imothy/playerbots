# Native cast escape policy — selected mechanics, not full raid coverage

This policy uses the existing dungeon strategy, reaction engine, spell data,
`MovementAction::MoveTo`, and native height/path checks. It neither changes boss
scripts nor grants/removes auras, fabricates threat, or teleports bots.

## Verified native mappings

| Expansion | Map / caster entry | Observed cast | Radius source |
|---|---|---|---|
| TBC/Wrath | Karazhan 532 / Aran 16524 | Arcane Explosion 29973 | 29973, radius index 38 (21 yards) |
| TBC/Wrath | Shadow Labyrinth 555 / Murmur 18708 | Sonic Boom 33923 / heroic 38796 | Native SpellEffects dummy dispatch to 33666 / 38795, index 39 (34 yards) |
| Wrath | Halls of Lightning 602 / Loken 28923 | Lightning Nova 52960 / heroic 59835 | Active cast, index 9 (20 yards) |
| Wrath | Ulduar 603 / Leviathan Mk II 33432 | Shock Blast 63631 | Active cast, index 18 (15 yards) |
| Wrath | Pit of Saron 658 / Ick 36476 | Poison Nova 68989 | Active cast, index 18 (15 yards) |

Verified against the local ManTech core scripts `boss_shade_of_aran.cpp`,
`boss_murmur.cpp`, `boss_loken.cpp`, `boss_mimiron.cpp`, and
`boss_krick_and_ick.cpp`, their instance headers, `SpellEffects.cpp`, and read-only
local TBC/Wrath `spell_template` plus `SpellRadius.dbc` on 2026-09-05.
The implementation looks up runtime spell radii; the table is an audit record,
not replacement spell data. Radius metadata missing, non-finite, or outside the
verified bounded geometry disables this policy rather than guessing a radius.

## Behavior and lifecycle

- Only a live engaged matching caster in the actual same map instance counts.
  Classic does not activate any of these expansion mechanics.
- The current native generic cast must still exist and match when executing a
  cached decision. Completion, interruption, reset, death and map/instance changes
  release the hold immediately, without a made-up post-cast delay.
- Escape outside the native radius with a two-yard positioning margin. At most
  eight candidate paths per one-second cached decision. No valid route means no
  fabricated destination and no movement suppression from this policy.
- Once safe, stop an old chase instead of walking back in before the cast ends.
  Stationary attacks/heals remain available. Movement-effect spells are gated
  during the hold; normal ground-hazard escapes retain precedence.
- Native Flame Wreath holding takes priority if Aran mechanics overlap. It does
  not remove the ring or force movement through it.
- No new grid scan, worker, SQL table, diagnostics counter or log file is added
  by this cast policy. It uses the existing attackers list. Unsupported maps
  return before allocating the calculated encounter value or inspecting spells.

## Required play tests / limits

Controlled actual-source tests cover expansion/difficulty selection, stale cast
and map state, invalid/missing radii, safe hold versus chase, permitted stationary
casts, movement-effect arbitration and bounded unreachable-path rejection.
They do not establish boss kills, healing throughput, client responsiveness,
complete path safety through every obstacle, or success while rooted/slowed.

Test each listed normal/heroic mechanic with melee, tank and healing roles. Check
that bots escape during the cast, preserve a stationary heal when already safe,
and resume ordinary combat afterward. In particular, Loken's distance-dependent
damage means the return after Nova matters; this is not complete Loken strategy.
No generic rule is inferred for other AoEs (some mechanics require staying in,
interrupting, using an object, stacking, or line of sight instead of running out).
