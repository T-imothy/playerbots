# Pet commands and expansion-specific cleansing

Source review, 2026-09-06. These fixes are on the testing branch. Actual pet
pathing/cast outcomes still require a running-world/client check.

## Pet spell admission (all three versions)

The old unit/gameobject/destination `CanCastSpell` shortcuts returned true for
any learned, ready pet spell. They did not check pet ownership, lifecycle,
target suitability, resources, GCD, immunity or control. The destination cast
also discarded its coordinates and sent an untargeted pet-action packet.

`CanCastPetSpell` now checks ownership/world/instance, life/teleport state,
CharmInfo, disabled actions, native AI script control and ongoing casts. It
mirrors `WorldSession::HandlePetAction`'s learned/nonpassive/target restrictions
and uses `Spell::CheckCast(true)` with the native pet flags and actual pet
caster. It does not call SpellStart, spend resources or change movement during
feasibility. The real packet is still dispatched by the existing session
handler, including Wrath's controlled-unit helper. Execution checks admission
again so an earlier successful feasibility result is not assumed current.

The handler's normal hostile out-of-range/LOS spell opener remains available;
its own path checks and ordinary pet AI still control movement. A submitted
packet is not proof a cast completed. A path can fail and range checks can
precede later native resource checks. We do not fabricate a successful cast,
clear cooldowns, bypass costs or teleport the pet. Unsupported gameobject and
coordinate requests no longer claim to be usable pet commands.

`PetAI::CheckPetCast` was also reviewed: it is a private auto-cast selector,
not a public command API. No access change or duplicated pet AI was introduced.
Human pet commands and the native handler itself are unchanged.

## Cleansing totems (different by expansion)

The local native spell records confirm Classic/TBC 8170 is Disease Cleansing
Totem and 8166 is Poison Cleansing Totem. Wrath has 8170 Cleansing Totem and no
8166 record. The old action keys named the removed spells; the already-written
Wrath action had no factory registration. The spell-name resolver had no alias.

Classic/TBC retain their two native spells. Wrath's existing `totem water
cleansing` and `totem water poison` commands both choose the learned Cleansing
Totem. The actual `cleansing totem` action is registered only in Wrath. Water
totem presence checks use the same per-era name as their actions, preventing a
name mismatch from repeatedly replacing a deployed totem. No strategy settings,
learned spells or database records are rewritten.

## Distance units

The coordinate-spell feasibility sight check applied sqrt to the default
`WorldObject::GetDistance(x,y,z)` result, which already returns a linear,
bounding-radius-adjusted distance. This admitted distant destinations. Remove
that extra root. Explicit `DIST_CALC_NONE` calls in battleground navigation
return squared distance in these cores; their sqrt calls are correct and were
deliberately left unchanged.

## Regression evidence and remaining checks

- `pet_cast_admission_regression.py`: actual admission and packet-dispatch
  methods with controlled native CheckCast outcomes, all three expansions.
  Includes owner/target lifecycle, range opener, unsupported target types,
  casting, missing metadata, cooldown, resource/control rejection and autocast
  packet flags. This is not a simulation of actual spell execution.
- `shaman_cleansing_regression.py`: actual action classes, factory entries and
  full water-totem trigger compiled for each expansion; current totem suppresses
  repeat selection and Classic/TBC do not gain Wrath's action.
- `cast_distance_units_regression.py`: actual spell sight check compiled with
  each core's real distance implementation and boundary cases.
- In-game: warlock/hunter pet attacks, buffs, dispels/interrupts, depleted
  resources, target death, pet death/revive, despawn/replacement and zoning;
  a hostile pet spell from out of range must still use ordinary pathing. Check
  both legacy shaman cleansing commands in Wrath and separate totems in TBC.

No new diagnostics, cache, worker, configuration or database migration.
