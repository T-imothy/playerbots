# Maexxna targeting and Web Wrap lifecycle

This continuation covers native script defects and a specific rescue priority,
not a full Naxxramas clear or complete role/phase coverage.

## Native corrections

All three cores enlarged the eligible-player vector to the desired Web Wrap
count. During a depleted raid or wipe, this inserted null pointers which were
then dereferenced by the cast loop. Selection now only truncates an oversized
list. Classic/TBC retain a maximum of three targets; Wrath retains one in normal
and two in heroic raid mode. Random target selection and distinct destination
spells remain unchanged.

Wrath's Web Wrap death hook removed boss selection spell 28673 from the trapped
player. Both boss selection spells, 28673 and 54127, are script effects rather
than the player's actual wrap aura. The hook now removes stun/damage aura 28622
and transform aura 28627, and preserves the existing display restoration.
Classic/TBC already remove those effects through their Clear Web Wrap script.

`maexxna_lifecycle_regression.py` executes the actual native selection method
with zero through eight eligible players, verifying era/difficulty caps and
unique destinations. It also executes Wrath's actual death hook and checks
removal of both wrap effects, preservation of unrelated auras, and missing
victim handling. Before-fix runs reproduce null target selection and the
incorrect release; after-fix runs pass on all three source trees.

## Bot rescue targeting

The existing dungeon priority action now includes map 533, boss 15952 and Web
Wrap 16486 in all three cores. It resolves the wrap's exact native summoner to a
living, non-charmed, non-teleporting player in the bot's group and requires the
actual wrap aura 28622. A single live engaged Maexxna must be available in the
same instance and phase. Missing sources, unrelated players, ambiguous bosses,
despawns and completed releases do not activate rescue priority.

DPS bots retain the selected valid wrap instead of switching repeatedly. The
native wrap self-stun is allowed for this rescue object, while breakable CC,
assigned CC targets and damage immunity remain protected. Manual attack/raid
target commands, real players, healers, tanks and the current boss victim retain
their existing control. The action resolves its target again before attacking.
Existing movement and cast admission checks still apply; this does not prove
that every melee bot can traverse to every elevated wall position.

`dungeon_add_priority_regression.py` executes this policy in all three build
variants, alongside the earlier dungeon rules. Fixtures include live/dead and
missing victims, group/phase/instance transitions, stale wrap auras, protected
targets, roles, manual commands and native self-stun. The missing priority was
reproduced before the change.

No DB migration or new configuration setting is required. Builds, installed
revisions and runtime verification are recorded separately in the task output.
