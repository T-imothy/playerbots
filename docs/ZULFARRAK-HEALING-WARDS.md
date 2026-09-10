# Zul'Farrak healing ward priority

Grouped DPS with the dungeon strategy prioritize Sandfury Witch Doctor Greater
Healing Wards in Zul'Farrak, then resume normal targeting when no eligible ward
remains. Tanks and healers keep their existing roles. Explicit attack commands
and raid-icon target orders retain the existing priority-add system's precedence;
mark a ward if manually directing the group to attack it.

The realm world databases were checked on 2026-09-10 for Classic, TBC and Wrath:
Sandfury Witch Doctor (5650) casts Healing Ward (11899), which summons Greater
Healing Ward (8179). Native Totem::GetSpawnerGuid resolves the summoner. The rule
requires map 209, the exact ward and owner entries, a live owner fighting a player
in this group, and ordinary attackability, distance and crowd-control checks.
It does not pull wards belonging to an idle or unrelated fight.

The existing dungeon priority-add action selects the ward and prevents DPS assist
from immediately replacing it. The current-target validator also recognizes this
specific eligible ZF objective while the dungeon strategy is enabled: passive
healing totems have no hostile victim and can otherwise fail the normal threat
test. Dead, unavailable or no-longer-eligible wards are not retained.

Validation: dungeon_add_priority_regression.py compiles the production selection,
priority preservation and current-target validation methods for all three core
defines. Cases cover passive wards, stable selection, death, reset, wrong owner,
unrelated group, map/instance/range, roles, manual orders, attackability and CC.
Existing raid-totem cases and healing target-recovery regression checks also run.
These controlled fixtures do not substitute for a live ZF gameplay test.

No native encounter scripts, world data, class rotations, healing thresholds,
healer positioning, addon files or configuration are changed.
