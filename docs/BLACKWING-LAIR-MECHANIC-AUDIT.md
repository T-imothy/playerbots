# Blackwing Lair native-mechanic audit — partial coverage

Suppression-room support is not a complete raid routine. This ledger records
native evidence and bot changes, not a claim of unattended raid completion.

## Nefarian priest call: implemented and regression-tested

All three native `blackwing_lair/boss_nefarian.cpp` scripts cast 23401.
`Spell::CheckTargetScript` restricts its recipients to priests. Each core's
`Unit::HandleOverrideClassScriptAuraProc`, override script 3656, triggers 23402
only for `IsSpellHaveEffect(spellInfo, SPELL_EFFECT_HEAL)`. Its native comment
explicitly excludes periodic healing such as Renew.

`EncounterSpellPolicy.cpp` follows the actual aura, not an estimated boss timer:

- Only living, uncharmed, non-teleporting priests in BWL with 23401 qualify.
- Automatic direct heals are rejected at usefulness selection and freshly at
  execution. Renew, shields, dispels and ordinary damage remain available.
- A reaction checks the existing generic/channel slots and interrupts only a
  harmful casting/channeling heal. In-flight/finished spells, movement and
  unrelated casts are not cancelled. Aura expiry releases the restriction.
- Wrath Penance follows the native priest-family dummy flag and `CanAssistSpell`
  branch in `Spell::EffectDummy`, preserving offensive Penance. That branch is
  excluded from Classic/TBC. Native healing Penance and Divine Hymn channels
  expose a direct-heal tick payload; at most three immediate payloads are read.
  No recursive spell graph, extra per-bot state or rank whitelist is used.

Tests compile the actual policy and complete usefulness/execution wrappers in
all three modes: aura arrival/expiry, Renew/absorb preservation, direct-heal
slots, channel payloads, missing/cyclic data bounds, offensive Penance, expansion
separation and fresh selective interruption. Native builds and client tests are
separate. Delayed Prayer of Mending proc ownership is not inferred from a direct
heal/channel test and is not declared solved here.

Remaining Nefarian: other class calls, shadowflame protection, fear/positioning,
phase transitions, construct assignments and wipe recovery.

## Other evidence collected; not complete bot routines

- Firemaw/Ebonroc/Flamegor Wing Buffet 23339 applies native -50% threat. Tank
  changes must use learned taunts and real threat, not direct threat assignment.
- Ebonroc uses Shadow of Ebonroc 23340; Flamegor uses Frenzy 23342.
- Vaelastrasz uses Burning Adrenaline 18173/23620 and native target selection.
- Chromaggus chooses two breaths in native instance state; affliction 23173,
  breath selection 23195 and frenzy 23128 need native-aware decisions.
- Broodlord's knockback/threat/room constraints, Razorgore's orb/event and the
  remaining BWL positioning/tank/support assignments remain open.

No boss script, spell effect, immunity, aura or DB row is changed. Existing
sampled action logs can observe `stop corrupted healing`, not prove a proc or
successful encounter. No new diagnostic file, thread or persistent cache.
