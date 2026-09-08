# Eating and drinking recovery correction

Date: 2026-09-08. Applies to Classic, TBC and Wrath through the shared playerbot cast helper.

## Fix

`PlayerbotAI::CastSpell(uint32, Unit*, ...)` now honors `SPELL_ATTR_ALLOW_WHILE_SITTING` when preparing a cast. The configured bot-supply eating/drinking actions can therefore remain seated and reach native spell execution instead of entering a repeated sit → stand → failed cast loop.

The actions retain correct `SetStandState` usage and truthful cast-failure handling. Spells without the native sitting permission still stand the bot up and return the existing retry delay. Native spell validation, aura application, resource restoration and interruption remain authoritative; the patch does not force an aura or resource change.

This is shared code for mana users drinking and any applicable class eating, without healer, spec or role exceptions. Real inventory item use follows a separate dispatch path. The existing potion fixes and healer enhancements remain included. No mana threshold, addon setting, encounter, database or configuration changes are required.

## Root cause

The persistent standing-start regression was introduced in fork commit `d19c5c7cbe4fda1eb9949f106364988fcf418692` while correcting two real action bugs: an invalid unit-state call used in place of actually sitting, and ignored cast-failure results. Correctly seating the bot exposed the older cast helper's unconditional stand-up/reject behavior. Each recovery retry then repeated the failure.

This attribution does not establish an identical upstream production incident. In the controlled comparison, the pre-regression code reaches the cast boundary from standing; the current pre-fix baseline does not. Removing only the action's sitting call fixes that first case but still fails when nearby-master posture mirroring seats the bot. Respecting the native spell attribute passes both cases.

## Validation

- The strengthened consumable regression compiles the real action bodies together with the helper's posture/facing preparation. It covers successful seated recovery, failed cast results, normal-spell stand-up/retry, combat rejection, non-mana eating and the inventory dispatch boundary. The previous fixture replaced the helper with a stub that omitted its posture behavior.
- Combined recovery, retained mana-potion reaction and potion cache/inventory regressions passed in all three expansion modes: nine runs. This is preservation coverage, not a new investigation or gameplay claim about potions.
- Five historical/alternative variants passed their expected results in all three expansion modes: 15 comparisons, including repeated seated-master posture mirroring. The upstream comparison uses fixed snapshot `993f18091e67565986cf55c4d9b8e6eae11223f9`.
- Each expansion's own `Spell.dbc` confirms Food 24005 and Drink 24355 carry the sitting permission. The matching CMaNGOS sources already check that attribute in native casting and handle recovery aura posture. No external emulator behavior is substituted.
- Release checks require all three native world builds, embedded core revisions, the shared source pin, matching EXE/PDB identities, remote baseline verification and installed-file hashes.

## Runtime limits

The compiled tests stop at a controlled native-cast boundary; they do not execute complete native spells or prove aura application and resource ticks. No dev-world startup or production restart is performed by this release, preserving the existing preference. Live recovery, interruption by combat/movement, real inventory consumption and grouped/autonomous behavior across PvE/BG/arena contexts remain runtime-unverified for these new binaries. The prior successful toggle checks and potion observations are not generalized into complete gameplay verification.

After a world-server restart, useful live confirmation is an eligible out-of-combat bot actually gaining the food/drink aura and increasing health/mana, including while its nearby master is sitting, then stopping recovery normally when combat or necessary movement intervenes. The `food` noncombat strategy and applicable supplies must still be available.
