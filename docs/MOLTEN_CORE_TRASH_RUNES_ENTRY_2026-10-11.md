# Molten Core trash, rune eligibility, and Lothos entry

## Read-only live audit

Classic, TBC, and Wrath use the same Firelord (11668) and Lava Spawn
(12265) EventAI timers. Firelords first summon after 10–15 seconds, then
every 15–20 seconds. A surviving Lava Spawn splits after 30 seconds;
the original despawns after summoning its two replacements. Descendants
can split again. Killing the parent stops its new summons but does not
remove living children. The audit found no incorrect timer or creature
binding requiring a world database migration.

Sources: [contemporary 2006 raid strategy](https://www.ironsongtribe.com/thread-4517-post-2877.html),
[Classic summon spell record](https://www.wowhead.com/classic/spell=19392/summon-lava-spawn).
Blizzard's published Firelord hotfix material located in this audit concerns
the later anniversary raid; it is not evidence of exact vanilla timers.
The 30-second figure above describes these live databases, not a claimed
Blizzard specification. No retained combat replay proves the cause of the
reported raid wipe.

## Bot behavior changes

- DPS now focuses engaged, attackable Lava Spawns before Firelords, including
  when the parent has a raid mark. With no living eligible spawn, it focuses
  a Firelord. Among spawns it prefers the lowest health, then stable GUID.
  Direct player attack commands, CC exclusions, healers, and tank assignments
  retain their existing behavior. Soul Burn receives native ready dispels.
- Classic/TBC rune movement and use require an actual Aqual or Eternal
  Quintessence, even when bot item cheats are enabled. Native usability and
  cooldown checks apply. Bots require the rune's associated encounter to be
  DONE and its native object to be ready. Combat, ongoing casts, active flames,
  already doused runes, and missing items prevent an attempt. Execution
  rechecks inventory and the object. Native spells consume the item or start
  its cooldown. No items are generated and no encounter state is forced.
- Wrath's instance script automatically extinguishes the runes, so its bot
  dousing routine is disabled.
- Lothos's accepted NPC teleport now captures nearby living, noncombat raid
  followers across all subgroups. This runs after the native gossip handler,
  and requires creature 14387, source map 0 and accepted destination 409.
  The existing bounded summon queue waits for the requester to land. Native
  access, bot control and public-companion save reconciliation remain in
  effect. Failed human entry, changed membership/controller, a new location,
  combat, or disabled follow cancels the automatic handoff. An already
  completed independent entry is not teleported again. Explicit summoning
  and human raid lockouts retain their existing policies.

The old urgent-transition follower route handled portal area triggers, not
Lothos gossip. This confirmed coverage gap can leave followers outside; it
does not prove why precisely one bot independently entered in the report.

## Validation and rollout

Actual production-body fixtures cover add selection, support dispels, rune
inventory/cooldowns and native state, and a 40-player Lothos entry with all
39 followers. The coordinator, binding, convenience summon, queue cleanup,
revival and ritual fixtures are run for compatibility. Native MSVC syntax
checks cover the changed implementations and action contexts for all three
core APIs. These checks do not simulate live map workers, client ACKs,
pathfinding or an actual raid encounter.

All three server versions require rebuilding and deployment to activate
these source changes, followed by a controlled realm restart. No SQL update,
client patch or cache removal is required. Production server binaries were
not compiled, deployed or restarted by this audit. Test executables are
isolated fixtures only. Live validation should confirm 39 followers enter
the requester's raid copy through Lothos, DPS switches to freshly spawned
Lava Spawns, itemless bots stay with the group, and a legitimate ready
Quintessence holder douses an eligible rune once.
