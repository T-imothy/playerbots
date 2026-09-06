# Native taunt targets and bounded encounter planning

## Righteous Defense: TBC/Wrath recipient correction

The action inherited `current target`, normally the enemy. Both native
`ClassScripts/Paladin.cpp::RighteousDefense` scripts instead inspect attackers
of a friendly unit and ask the caster to taunt up to three of those attackers
with 31790. Local TBC/Wrath spell 31789 uses friendly target type 21. These
native rules do not turn an arbitrary hostile target into the correct ally.

The automated action now uses a fresh `righteous defense target` value: the
live group player currently being attacked by its current enemy. It requires
actual native attacker membership, native assistance admission and valid
world/group/phase/lifecycle state. Normal reach prerequisites use that same
recipient value, not the enemy. A missing recipient at execution returns
failure rather than passing a null target down the spell path. The core still
owns resource/cooldown checks, attacker choice, taunt resistance and threat.

It does not steal from a healthy fellow tank. Classic's value returns null;
no TBC spell is created or learned in Classic. Wrath retains Hand of Reckoning
as the existing first choice and Righteous Defense as its existing fallback.
The selector intentionally concerns automated tank rescue of group players,
not new NPC-escort/pet or explicit player-command targeting behavior.

## Ebonroc tank swaps: all three cores

The generic lose-aggro trigger refuses to steal another tank's target. That is
normally correct, but it also prevented a clean off-tank responding to native
Shadow of Ebonroc (23340, boss 14601/map 469). The three native scripts cast
this debuff on their current victim; native spell data triggers 23394.

The trigger now admits this specific mechanic when the current group tank
has the boss-owned debuff and the responding tank is clean. Existing class
taunt/stance/form routines do the work; no forced target, threat edit, aura
removal, timer or spell grant is used. Automatic taunt dispatch rechecks the
live victim so a queued second taunt cannot bounce the boss back to a dirty
or previous tank after another tank has already taken over. Ordinary rescue
of a non-tank victim remains unchanged. Righteous Defense uses the same swap
decision for its friendly recipient. Explicit custom cast commands are not
rewritten by this automatic-action policy.

## Planner caching correction

`CalculatedValue::Get` uses the legacy expression `checkInterval / 2`.
With an integer interval of 1, that becomes zero and calculation occurs on
every read, including multiple action/trigger/multiplier reads in one update.
The new Magtheridon, Gruul, Naxx, BWL and boss-cast position values now use 2,
which yields the intended one-second cache under existing framework semantics.
No framework-wide timing change was made. Immediate combat target/health
values and Flame Wreath holding remain immediate. Destination/lifecycle and
spell checks still run again before movement/click dispatch.

The controlled timing test reproduces ten calculations for ten reads at
interval 1 versus one at interval 2 in the same second, then recalculation
after one second or reset. This is not a measured server CPU/RAM percentage.
The cached data is one position/GUID plan per participating AI, not a queue.

## Verification and player tests

- `encounter_taunt_regression.py`: actual trigger/policy/recipient code in all
  three eras, native script contracts, dirty/clean tank, already-completed
  swap, wrong boss/map, missing spell/attacker, group/phase/death/logout gates.
- Existing cast-wrapper tests verify the admission guard both before scheduling
  and at dispatch. Existing native casting remains the final authority.
- `encounter_planner_cache_regression.py`: actual legacy getter with only the
  clock substituted, plus constructor configuration checks.
- Live tests remain necessary: TBC paladin rescue of a group member, Wrath
  fallback with Hand of Reckoning unavailable, Ebonroc two-tank swap/resist/
  cooldown cases and no repeated taunt-back after the swap.

No SQL, configuration, optional diagnostic logger, worker or public API change
is required. These are functional corrections, not diagnostic code to remove.
