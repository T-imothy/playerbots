# Encounter lifecycle and objective continuation

This continues the full [raid/dungeon register](RAID-DUNGEON-AUDIT-20260906.md).
It records implemented mechanics and native fixes, not completed raid clears.

| Encounter | Change | Scope |
| --- | --- | --- |
| Thekal | DPS balances the living trio with five percentage points of target hysteresis; below ten percent it finishes Lorkhan, Zath, then Thekal. Native fake-death actors remain identifiable but cannot be damage targets; tiger form ends this rule. | All three cores |
| Ayamiss | Native paralysis code handles both target searches returning empty before casting, recording a target GUID or summoning a larva. | All three cores |
| Gluth | DPS prioritizes native trigger-summoned zombies reduced to five percent health, favoring ones closer to Gluth. It accepts the passive, victimless state used after Wrath Decimate. Healthy zombies retain normal selection. | All three cores |
| Shaffar | DPS prioritizes his summoned beacons and static beacons already engaged by the group. Idle beacons are not pulled by this rule. | TBC/Wrath |
| Warp Splinter | DPS targets the boss's actual sapling summons. | TBC/Wrath |
| Ichoron | DPS targets his attackable globules, including surviving globules after the first merge ends his split. | Wrath |
| Jedoga | DPS targets an attackable volunteer during Hover Fall, excluding volunteers still protected by Sphere Visual. Native intro state and visual timer now have defined defaults when the initial visual cast fails. | Wrath |
| Bronjahm | DPS targets fragments actually created by a group member's Draw Corrupted Soul (68846). It does not require Corrupt Soul, which expires before the summon. | Wrath |
| Viscidus | A split requests one bounded wave, initializes tracking before triggered summons, and processes a glob's death/arrival once. Full-health summoning cannot index past the twenty-spell array. | All three cores |
| Viscidus bots | DPS uses learned first-rank Frostbolt/Frost Shock and Wrath Icy Touch while his native frost weakness is active. Pure frost school, normal cast feasibility and current-target checks apply. His self-applied freeze is excluded from ordinary CC avoidance; explicit CC-marker assignments remain. DPS targets actual boss-summoned globs. | All three cores, with class/era gates |
| Ossirian | Native replacement-crystal search includes its final candidate, respects a zero request, and first-crystal initialization handles missing instance data. | All three cores |
| Karathress/Tidalvess, Halazzi | DPS prioritizes Spitfire and Corrupted Lightning Totems using native totem ownership and the owner's current group victim. Spitfire remains recognized after Karathress inherits it. | TBC/Wrath |
| Moam | DPS warlocks, priests and hunters prioritize their normal learned-rank mana drain/burn/sting above 25 percent boss mana. Existing Viper Sting is preserved. During Energize, normal attackable Mana Fiends receive priority; healer/tank roles and assigned CC remain. | All three cores |
| Sartura and royal guards | Escape considers every current native whirlwind, validates the entire route against those moving hazards, and rechecks queued endpoints. The native periodic payload handles a parent aura/effect disappearing before execution. | All three cores |
| Fankriss / Kurinnaxx | Fankriss's actual worm summons receive DPS priority; both bosses use the existing coordinated tank-swap policy at three native Mortal Wound stacks. Manual targets, assigned CC, healer roles and taunt feasibility remain. | All three cores |
| Yauj | Brood summons receive their own threat and attack target; the callback no longer applies those operations to the dying boss. Empty selections remain safe. | All three cores |
| Whitemane, Akama channelers, Paletress, Marrowgar | Correct inverted native cast-result checks. Cooldowns and one-shot completion now follow CAST_OK; failed casts retain their retry opportunity. | Whitemane all three; Akama TBC/Wrath; Paletress and Marrowgar Wrath |
| Paletress memory | DPS recognizes all 25 native memory templates while her Reflective Shield is active, requiring actual boss ownership and normal attackability/CC checks. | Wrath |
| Loken | Between Lightning Novas, return within five yards to reduce the native distance-scaled Shockwave. Preserve current casts during the return, leave the active tank anchored, and invalidate the return immediately when Nova starts. | Wrath |
| Vexallus | Advance summon thresholds only after successful native casts. Track each heroic half independently across retries; reset clears partial progress. Failed Overload remains eligible for retry. | TBC/Wrath |

Target-selection dispatch preserves real-player control, explicit attack/raid
targets, healer and tank roles. World, life, phase, charm, teleport, native
attackability, range and ownership checks are repeated as appropriate. These
rules do not replace Gluth kiting assignments, force every caster into melee
during Viscidus's shatter phase, or certify complete dungeon routes.

Development spell rows verified the summon effects, template identities and
Shaffar's normal/heroic beacon timers. Actual-method regression runners cover
the rules above; the Viscidus lifecycle fixture also simulates synchronous
duplicate summon callbacks, duplicate deaths, arrival after death, death after
arrival, reset, failed casts and health percentages through 100 percent.

The earlier Thekal/Ayamiss checkpoint passed 112 regression runners and all
three native builds. Isolated native startup/shutdown checks passed at 54.14s
Classic, 79.16s TBC and 143.28s Wrath, with runs overlapping on the dev PC.
Those startup timings precede the Gluth/dungeon/Viscidus additions. The later
Gluth/five-dungeon/Jedoga source checkpoint also built in all three cores.
Subsequent Viscidus changes require their own full build/suite checkpoint.

The Viscidus checkpoint subsequently passed all three native builds and all
117 regression runners. That checkpoint precedes the Ossirian/totem/Moam
additions and a follow-up making the special Viscidus frost action respect the
normal skipped-spell settings. Their targeted regression checks pass; they need
their subsequent native build/full-suite result recorded separately.

The Ossirian/totem/Moam checkpoint subsequently passed all three native builds
and 119 runners. Sartura subsequently passed all three native builds and 120
runners, including uncached overlapping whirlwind routes. These results precede
the Fankriss/Kurinnaxx/Yauj/cast-result additions, whose focused tests pass.

The Fankriss/Kurinnaxx/Yauj/cast-result checkpoint subsequently passed all three
native builds and all 122 runners. A scan of 73/206/305 JustSummoned callbacks
in Classic/TBC/Wrath found no further direct boss-threat/unqualified-AttackStart
pattern after the Yauj fix. This is a specific ownership check, not proof of
every summon lifecycle. Paletress/Loken/Vexallus focused tests pass; their full
build/suite checkpoint is separate.

The prepared TBC and Wrath encounter metadata migrations were applied to local
development databases with before/after snapshots, rollback SQL and idempotence
checks. Production databases/shares and ManTech baselines were not changed by
this continuation. There is no new SQL or configuration requirement for the
source changes in the table above.
