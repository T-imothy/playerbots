# Karazhan native add priorities (TBC/Wrath)

2026-09-06 source audit. This is partial encounter support, not a complete
Karazhan clear. Classic compiles a no-op selector and gains no TBC mechanics.

## Illhoof: destroy actual Demon Chains

Both native `boss_terestian_illhoof.cpp` scripts cast 30120 from Illhoof after
Sacrifice 30115; the local spell records summon entry 17248. The script makes
the chains passive. Killing the chains lets that same native script remove
the victim's Sacrifice. Removing Sacrifice normally despawns the chains.

A generic attacker/threat-victim filter can exclude a passive chain. The new
selector therefore uses the existing nearby `possible targets` value, native
attack permission/free-move rules and the shared CC/tap/range checks. It requires
an alive, engaged Illhoof (15688), a living same-group sacrifice victim whose
aura caster is that boss, and chains whose native `GetSpawnerGuid()` identifies
that same boss. No forced aura removal, kill, teleport or fabricated threat.

## Curator: clean up the native Astral Flares

Both native Curator scripts and the local TBC/Wrath spell records use four
flare entries: 17096, 19781, 19782 and 19783 (summons 30239, 30236, 30240 and
30241 respectively). The selector prioritizes only those summoned by the
currently engaged Curator (15691), retains a valid current flare to avoid
switching back and forth, and falls back to ordinary combat when none qualify.

Curator's arcane immunity/power-drain immunity, evocation, hateful-bolt target
and enrage are still native mechanics. No damage/resistance edits or special
cooldown-spending routine is introduced here.

## Shared controls

- DPS only. Healers, configured tanks and the actual current boss victim retain
  their jobs. No automatic pulling or target priority outside active combat.
- Live explicit attack orders and valid raid marks remain authoritative.
  Assigned CC, current breakable CC, roots/stuns/fears and normal core attack
  admission remain respected. Ambiguous simultaneous boss contexts opt out.
- The action recomputes its target during execution via existing AttackAction.
  It stores no Unit pointer/state, adds no scan/worker/SQL query, and uses the
  existing spell rotations and pet/attack path after target selection.
- The priority multiplier only suppresses generic `dps assist` while an actual
  priority target exists. It does not block class casts, healing or hazard moves.

`karazhan_priority_regression.py` compiles the actual selector/arbitration for
all three eras and tests passive chains, four flare IDs, spawner/aura ownership,
current-target stability, death/despawn/zoning, group changes, manual orders,
CC and healer/tank exclusions. Native script/temporary-spawn contracts are also
checked. In-game tests are still needed for the real encounter timing and
nearby-target value population; these fixtures are not a raid playthrough.

Follow-up audit also found Onyxia/Pathaleon add selectors respected raid marks
but omitted the explicit `attack target` order check. They now preserve a valid
command and ignore a dead/out-of-instance cached mark; existing add priorities,
phase rules and native attack checks are unchanged.
