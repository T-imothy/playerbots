# Uldaman healing wards

Grouped DPS bots using the dungeon strategy prioritize Healing Ward (3560) on
map 70, summoned by Stonevault Oracle (4852) or Stonevault Shaman (2894) through
native spell 5605. These entries and casts were verified in all three production
world databases. The ward's living summoner must be fighting this group.

The selected passive ward survives target validation on subsequent AI ticks;
normal DPS assist cannot immediately replace it. Manual targets and raid markers
retain precedence. Tanks and healers retain their existing role assignments.
Wrong owners, maps, instances, friendly/protected targets and other groups are
excluded. No native creature scripts, spells or database records are changed.

The expanded dungeon-add regression exercises Uldaman and existing Zul'Farrak
wards under all three expansion defines, including selection, preservation,
roles, ownership, manual targets and stale targets. Live dungeon confirmation
remains separate from these compiled regression checks.
