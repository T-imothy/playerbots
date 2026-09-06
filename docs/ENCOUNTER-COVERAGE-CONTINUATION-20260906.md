# Remaining encounter coverage — source inventory checkpoint

The continuation enumerated native boss script registrations and read-only dev
`creature_template` mappings in Classic, TBC and Wrath, then searched Playerbots
for candidate name, entry and spell references. The CSV is in the task output:
`Playerbot-Audit-Continuation-20260906/native-encounter-inventory.csv`.

| Core | Native script rows | Instance directories | Rows without candidate references |
| --- | ---: | ---: | ---: |
| Classic | 101 | 21 | 15 |
| TBC | 235 | 46 | 30 |
| Wrath | 359 | 68 | 83 |

These are **script registration rows, not unique bosses or a coverage percentage**.
They include adds/components and older content in later cores. A match in a gear
table, shared spell, comment or an excluded expansion branch does not implement a
mechanic. Spell constants collected from a multi-boss native source file are file
context, not a per-boss cast assignment. Every CSV row therefore leaves completion
unestablished and requires mechanic-level review.

## Evidence from existing behavior

`DungeonStrategy` activates named Naxxramas, Onyxia, Molten Core, Blackwing Lair,
Karazhan and Mechanar strategies. Shared hooks additionally handle selected
Solarian priorities/bomb positions, Magtheridon cubes/Debris, Gruul Shatter,
curated boss-cast escapes and hostile ground hazards. This is partial support.

The existing native-mechanic reports and regression suite cover specific policies:

| Area | Existing source evidence | Still not established |
| --- | --- | --- |
| MC / Onyxia / BWL | Named strategies, CC-safe priorities, selected bombs/phase guards, Nefarian heal policy and selected tank rules | Every boss phase, complete assignments, raid recovery and kills |
| Karazhan / Mechanar | Named strategies, selected chain/flare/beam and cast handling | All Opera/event variants, all bosses and difficulty variants |
| Gruul / Magtheridon / TK | Selected Shatter spread, cube/debris, Solarian and Void Reaver support | Full Council/channeler/Al'ar/Kael'thas tactics, live coordinated mechanics |
| Naxxramas | Entry/exit lifecycle, selected burst separation, harmful-dispel policy and Thaddius charge separation | Complete wing assignments; Thaddius phase one/jumps/same-charge grouping |
| Other raids | Candidate references in the native inventory | Full ZG/AQ, SSC/Hyjal/BT/ZA/Sunwell, OS/EoE/VoA/Ulduar/ToC/ICC/Ruby Sanctum and world-boss review |
| Other dungeons | Curated Murmur, Loken and Ick cast handling, plus generic combat support | Encounter-by-encounter normal/heroic behavior across all three expansions |

The curated cast policy identifies native map/caster/cast combinations and uses
runtime radii. Aran's Flame Wreath takes precedence over explosion escape; Void
Reaver leaves the active tank in place. These isolated policies are not whole
encounter solutions. Nefarian/Grobbulus policies have payload-aware casting and
dispel guards, but cannot retroactively remove a previously deployed cleansing
totem or every pre-existing periodic effect.

## Audit disposition

The inventory is complete for the script registrations found by this scan. The
remaining **mechanic-by-mechanic audit is not complete**. This pass fixes concrete
shared pathing and queued-healing defects; it does not add a new full raid strategy
or declare missing encounter routines implemented. Keep areas 3–5 open until each
mechanic has a native-source mapping, reachable bot behavior, targeted tests and
appropriate live validation. Areas 1–2 retain their sustained-combat/class matrix;
area 7 retains real movement/load testing; area 6 remains deferred.
