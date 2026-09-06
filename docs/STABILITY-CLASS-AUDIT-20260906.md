# Stability and class/support audit — September 6, 2026

Scope: continue work areas 1 and 2 on the local enhancement branches. The user
deferred work area 6 (live client/release work). This change does not deploy,
publish, merge ManTech baselines, alter databases/configuration, or change dual
spec/training dummies. The accompanying core change guards skill auto-training.

## Corrected defects

| Area | Before | Corrected behavior |
| --- | --- | --- |
| Target reset | Current/pull target GUIDs survived the inherited raw-pointer reset; lazy reads bypassed their resolver. | Reset dispatches through their setters; lazy reads resolve the current GUID. |
| Lazy value initialization | Several calculated value constructors marked the cache as checked before calculating it. First lazy reads could use an uninitialized pointer or an uncomputed empty list. | Values initialize safely; the first lazy access calculates the value. Ordinary cache intervals remain unchanged. |
| Aura ownership | Numeric lookup examined the first caster's same-spell effect and could miss the bot's copy. | Native caster-specific holder lookup finds the bot's own disease/DoT, including multiple Death Knights. The previous null-dereference hotfix remains covered. |
| Group membership | Member enumeration dereferenced an empty group reference. | Missing references are skipped and enumeration continues. |
| Group count | `return count++` returned zero on the first matching bot. | All eligible matching bots are counted. |
| Mana recovery | A completely empty mana bar meant “has no mana,” disabling mana recovery/conservation checks. | Resource capability depends on maximum mana; empty casters still request recovery. |
| Mana percentages | A resource-less target divided by zero. | Zero-capacity/absent targets return the existing neutral percentage; calculated percentages are bounded and use wide arithmetic. |
| Readiness | Groups ignored completely empty mana bars; ready checks compared mana against the health threshold. | Empty casters participate in group readiness; ready checks use the mana threshold. |
| Innervate | Integer division treated most partially filled bars as 0%, while actually empty bars were rejected. | Both action and trigger use the configured low-mana boundary, including 0%, with zero-capacity protection. |
| Offensive mana use | Mana percentage alone cannot distinguish a non-mana target. | Viper Sting/Mana Burn require mana capacity; Serpent Sting still works against non-mana targets. Mana Tap requires actual available mana. |
| Assigned support | Map/instance ID checks alone admitted departed/different-phase or hostile group members. | Action and trigger use the native world/map/phase and friendly checks. Rebirth can still select a valid dead group member. |
| Core skill training | SkillLineAbility entries for missing spells were repeatedly passed to `addSpell`/`learnSpell`. | All three cores validate the spell template before training. Skill removal still visits missing entries for cleanup. |

## Evidence and verification

Actual-source C++ regressions reproduce failures before the target reset,
cache initialization, Innervate, mana-state, aura-owner, and skill-training
corrections. Added fixtures cover resource thresholds, other casters' identical
diseases, missing targets, group transitions, map/phase changes, resurrection,
and normal skill/rank/profession training. Existing class/proc, healing, threat,
interrupt, dispel, pet-casting and encounter regressions are retained.

Wrath's local SkillLineAbility.dbc row 21723 refers to absent spell 75460,
skill 253, race mask 1791, class mask 8, minimum skill 1, acquire method 2.
The production and local skill DBC SHA-256 both equal
`4154b833d6a26b9b9ce53851d56cb594f0813c0936a72ec89f933cc69abe42c3`.
`UpdateSkillTrainedSpells` processes that entry during skill training; the
regression proves the unwanted grant attempt before the guard and its absence
afterwards. This is separate from the repaired Pestilence crash. No live DBC
or database edits are required for this correction.

Final regression/build results and exact local revisions are recorded in the
task's output audit report. The shared source includes core-facing regressions
that expect the sibling enhancement core directories.

## Limits of this checkpoint

These are verified source corrections, not a claim that every rotation,
encounter, or transition has been exhaustively validated. Sustained gameplay,
all respec/charm/wipe sequences, channel timing under latency, and real pet
pathing remain unproven without further integration/client testing. No bot
improvement percentage can be established from regression tests or compilation.
Encounter areas 3–5 and release area 6 are outside this change.
