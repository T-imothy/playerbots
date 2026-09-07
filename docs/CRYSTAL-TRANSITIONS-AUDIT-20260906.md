# Crystal transitions and active aura-source targets

## Native TBC and Wrath script corrections

Selin Fireheart's crystal approach called `GetContactPoint` on Selin with the
crystal as the searcher. The native helper places a point near its receiver, so
this generated a point near Selin instead of near the selected crystal. The
receiver/searcher are now reversed. The regression executes the native selection
method and inline contact helper against distinct actor positions and heights.
Missing-crystal and currently-casting cases retain their existing behavior.

Kalithresh disabled normal combat and melee before looking for a distiller. If
none existed, the transition left him in scripted movement state without a
destination. He now enters that state only after finding a distiller. Both
successful and unsuccessful searches reset the existing 35–45-second timer;
missing targets leave normal combat running and do not repeat the regen speech.
The native-method regression reproduces the disabled-combat case before the fix
and checks both branches afterward in TBC and Wrath.

## Playerbot target rules

The existing dungeon add action now also recognizes these active sources:

| Map | Boss | Source | Aura on boss | Scope |
| --- | --- | --- | --- | --- |
| 545 | Kalithresh 17798 | Naga Distiller 17954 | Warlord's Rage 31543 | TBC/Wrath |
| 585 | Selin 24723 | Fel Crystal 24722 | Mana Rage 44320 | TBC/Wrath |
| 619 | Nadox 29309 | Ahn'kahar Guardian 30176 | Guardian Aura 56153 | Wrath |

The exact source GUID must be the caster of the matching boss aura. Static
crystals therefore need no invented summon ownership or nearest-boss guess.
Nadox's guardian uses the same direct aura-source proof; the native guardian
casts 56151, which periodically triggers the school-immunity aura 56153.

Local dev spell-script target rows independently bind 31543/37076 to Kalithresh,
44320/44321 to Selin and 44329 to Fel Crystals in both later eras. The collected
spell data confirms the Nadox 56151 -> 56153 chain. These are read-only findings;
the implementation needs no data migration or new config line.

The action still excludes healers, tanks, real players and the boss's current
victim. It preserves manual targets, raid-target commands and CC, rejects invalid
or immune adds, and checks world/instance/phase/liveness again. A closer inactive
crystal does not replace the active one. Multiple eligible bosses, including
Steamrigger and Kalithresh together, remain ambiguous and yield no priority.
Existing summon-owned add rules and the Vorpil helper chain remain intact.

The extended actual-source regression covers these cases in all three compile
variants, including Classic/later-era gates. It does not establish full encounter
clears, achievement completion, role assignments or normal/heroic progression.
In particular it supplies no coordinated Respect Your Elders strategy.
