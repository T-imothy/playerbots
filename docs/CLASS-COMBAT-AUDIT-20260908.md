# Class combat repairs — 8 September 2026

This release follows the priest/shared-healing release at playerbots `72800536`. It covers confirmed defects found while reviewing the ten class implementations, shared action scheduling, consumables and PvE/PvP combat strategies. Existing healer and warrior repairs are retained.

## Shared behavior — Classic, TBC and Wrath

- The opening attack wait correctly recognizes hostile players. Ordinary PvE pull waiting remains enabled when configured.
- Urgent healing can proceed during the opening attack wait; damaging actions retain the wait.
- Safe-distance movement checks both sides of its search arc and uses a fractional angle offset.
- Generated food and drink set the actual sitting posture instead of a melee-attacking state bit. Failed rest casts no longer report success or impose a full rest delay.
- Declined PvP potion/healthstone use reports failure so existing alternatives can run. The configured use chance and cooldown suppression remain intact.
- Bandages reject periodic percentage damage and leech as well as ordinary damage-over-time effects.
- Escape Artist retains the shared spell eligibility checks.

## Class repairs

| Class | Changes and expansion coverage |
|---|---|
| Warrior | Prior pull, interrupt, stance, threat and combat-consumable repairs rechecked. Shared wait/consumable corrections apply in all three eras. |
| Paladin | Judgement checks shared spell eligibility and the action's selected target. Seals retain shared buff eligibility. All eras; native spell availability still governs use. |
| Hunter | Auto Shot and pet dismissal retain shared eligibility. Classic trap preparation refreshes the learned trap rank and checks native feasibility. TBC/Wrath Steady Shot uses the native cast/GCD duration without an extra artificial GCD. Wrath gains its missing regular Steady Shot filler below primary shots, with Auto Shot activation ahead of the filler. |
| Rogue | Stealth and Vanish use shared execution/duration handling and retain flag-carrier exclusions. Preparation checks learned long cooldowns in the native reset pool for each era, including Wrath's glyph. It no longer relies on three identical IDs across expansions. |
| Priest | Prior Fade, healing selection, emergency healing and expansion-specific spell repairs rechecked. Shared attack-wait correction prevents delaying urgent heals. |
| Shaman | Rotation/proc ownership, healing and PvP routes rechecked; shared corrections apply. No additional shaman-only change was confirmed in this pass. |
| Mage | Polymorph preserves the selected crowd-control target, shared eligibility and actual cast duration, including the existing speed override. |
| Warlock | Pet summons and Inferno retain shared spell checks; a dead matching pet no longer prevents resummoning. Life Tap checks current health and shared eligibility. Wrath stops scheduling obsolete active Siphon Life and Amplify Curse actions; Classic/TBC retain their active versions. |
| Druid | Prowl reports cast failure and uses shared timing; Prowl and Travel Form retain shared eligibility. Ravage is selected from behind its target, matching the native positional requirement. Existing Pounce selection is preserved. |
| Death knight | Wrath only: Rune Tap selects self as a healing action; Blood Tap selects self as a buff. Deathchill no longer forces an unnecessary Frost Presence switch. Passive Unholy Blight is no longer requested as an active cast. |

## Expansion-specific consumables

- TBC/Wrath potions are excluded from arena use.
- Generated healthstones use native expansion items and level requirements: Classic ends at Major; TBC uses Master from level 60; Wrath adds Demonic at 63 and Fel at 69. Stones already in inventory take precedence.

## Review evidence and limits

The review followed class trigger/action mappings, defaults, prerequisites, custom usefulness/feasibility/execute overrides and shared duration/cooldown/consumable paths. Native spell definitions and core scripts resolved disputed behavior, including Preparation's reset masks, passive Wrath talents, self-targeted death knight spells and healthstone item IDs.

Several leads did not justify changes: shaman totem-bar trigger aliases resolve to the same predicate; native pet-targeted hunter buffs do not require an enemy target rewrite; dynamic paladin blessings choose their spell during feasibility; player threat calculations already exclude enemy players. Frost death knight DPS presence policy was retained while removing Deathchill's conflicting prerequisite.

Ten regression suites exercise actual changed C++ methods and existing combat/healing guards. Full native builds are required for all three eras before publication/deployment. Tests cover controlled behavior, not a live playthrough of every spec, encounter, arena or battleground. No claim is made that all possible combat bugs or optimal rotations have been proven absent. PvP queue/objective navigation is outside this class-combat pass.

Deployment replaces matching `mangosd.exe` and `mangosd.pdb`. No database, configuration or addon changes are required. The separate saved encounter-audit edits are excluded from this release and resume afterward. Realms use the new files after restart; gameplay confirmation follows restart.
