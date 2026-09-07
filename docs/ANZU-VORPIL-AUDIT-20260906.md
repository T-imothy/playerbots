# Anzu lifecycle and Vorpil add targeting

This continuation changes the local enhancement branches only. It needs no new
database rows or configuration lines. Native builds and runtime results belong
in the accompanying task receipt, not inferred from the source tests below.

## Anzu: TBC and Wrath native scripts

The brood action checked `m_healthBanishCheck`, although it decremented the
separate `m_healthBroodCheck`. That delayed the first spawn until below 70%
instead of the existing 73% brood threshold. If Banish could not cast, subsequent
updates could summon another six broods each time. The action now checks its own
threshold. The original 73/33% brood and 70/30% Banish thresholds are preserved.

The bird spirit constructor initialized duration but left `m_refreshTimer`
uninitialized. Its first active update could postpone the buff for an arbitrary
duration. Initializing that timer to zero makes the first active update cast the
native bird buff; subsequent pulses retain the existing two-second cadence.

`anzu_lifecycle_regression.py` executes extracted native methods from both cores.
Separate pre-fix runs reproduced the wave and timer failures. Tests cover strict
thresholds, repeated failed Banish attempts, action admission, two waves, reset,
all three birds, poisoned allocation storage, activation, pulse cadence, shorter
duration refresh and expiry. These are controlled native-method tests, not live
Anzu clears or proof of complete spirit assignments.

## Vorpil: TBC and Wrath bot behavior

In map 555, Vorpil (18732) creates a passive Voidwalker Summoner (19427), which
casts the five traveler summon spells. Its Void Travelers (19226) chase Vorpil
and cast Shadow Nova plus normal/heroic Empowering Shadows when close to him.
The native summon ownership is therefore traveler -> summoner -> Vorpil.

The dungeon add action now resolves exactly that two-level chain, requiring a
live uncharmed summoner in the bot's instance/phase and a live engaged Vorpil.
DPS bots can select these travelers while tanks, healers and the boss's current
victim retain their roles. Manual targets, raid target commands, crowd control,
immunity, target validity and dispatch rechecks remain in effect. The current
valid add is retained to avoid needless switching. No nearby-boss fallback or
unbounded parent traversal is used. Classic does not activate this encounter.

The extended `dungeon_add_priority_regression.py` reproduced the missing target
before the change and passes after it in all three compilation variants. It
tests missing/dead/charmed/wrong-entry/cross-instance/cross-phase summoners,
self/cyclic/unrelated ownership, boss reset/death, role and command exceptions,
CC/immunity and despawn. Native script identifiers and summon flow are checked
in both later cores. Full Vorpil movement, Rain of Fire and actual normal/heroic
group runs remain gameplay validation work.

## Adjacent lifecycle inspection

The nearby Vorpil summon timer and Shadow Labyrinth door timer are explicitly
initialized. Murmur's two old scalar timer declarations are unused by the native
implementation; the active events use CombatAI timers. They do not establish
another uninitialized read. No additional patch was made on that basis.
