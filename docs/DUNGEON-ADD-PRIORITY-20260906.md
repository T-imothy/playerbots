# Dungeon add priorities

DPS bots now select specific boss-owned adds in four encounters, rechecking the
native summoner and encounter condition each time the attack executes:

| Encounter | Condition and priority | Cores |
| --- | --- | --- |
| Mekgineer Steamrigger, map 545 | Mechanics 17951 summoned by engaged Steamrigger 17796. They follow him and use native Repair 31532/37936. | TBC, Wrath |
| High Botanist Freywinn, map 553 | Frayer Protectors 19953 summoned by Freywinn 17975 while Tree Form 34551 is active. The native last-add death callback ends Tree Form. | TBC, Wrath |
| Anzu, map 556 | Brood 23132 summoned by Anzu 23035 while Banish Self 42354 is active. Native brood deaths release banish. | TBC, Wrath |
| Anomalus, map 576 | Chaotic Rifts 26918 summoned by Anomalus 26763 while Rift Shield 47748 is active. The native last-rift death callback removes the shield. | Wrath |

Selection preserves a live current priority add to avoid oscillation. Ordinary
DPS assist does not immediately switch the bot back to the boss. The action does
not redirect healers, assigned tanks, the boss's current tank, or real-player AI.
It respects explicit attack commands and raid targets even when that target is
temporarily immune; this matters for intentional achievement strategies such as
Chaos Theory. It rejects stale, dead, charmed, immune, crowd-controlled, forbidden,
out-of-range or foreign-instance adds. Ambiguous different boss owners release
the override. Passive summoned adds can qualify without their own threat victim.
The native attack and movement pipeline still performs attack/path admission.

`dungeon_add_priority_regression.py` executes the production selection and
arbitration methods for all three eras. It covers all four encounter entries,
phase expiry, reset/death/despawn, wrong summoners, multiple owners, instance and
phase isolation, manual shielded-boss commands, role exclusions, CC, range and
target stability. Source-contract checks bind the cases to the native boss
callbacks and summon ownership API. These controlled tests and native builds
do not establish live dungeon clears. Healer bird-spirit assignments, routing,
achievement coordination and other mechanics remain separate encounter work.

No new database migration, configuration setting or baseline merge is needed.
