# Blackwing Lair playerbot combat audit — 2026-09-22

Only playerbot decisions were changed. Boss scripts, raid mechanics, encounter
state transitions, spells, loot, and databases remain unchanged. All three core
baselines consume the same shared playerbots revision.

## Boss coverage

| Encounter | Existing coverage retained | Additions in this revision |
|---|---|---|
| Razorgore | Normal tank/healer/CC behavior and native charm restrictions | Prioritize engaged Grethok and defender mages; protect Razorgore from direct bot targeting/offense until native egg completion; preserve an active boss tank |
| Vaelastrasz | Burning Adrenaline separation, including after boss death; current tank stays planted | Attack movement no longer bypasses separation holds; melee DPS uses rear flanks instead of directly behind the tail |
| Broodlord Lashlayer | Normal threat management and suppression-device rogue support | Ranged/healers hold outside the native Blast Wave radius; active tank and melee positions are retained |
| Firemaw | Native-LOS cover at five Flame Buffet stacks, holding until cleared; healer cover retains LOS to the tank | Extend the existing coordinated native-taunt policy to hand off a tank at five stacks to a clean, ready bot tank |
| Ebonroc | Existing coordinated Shadow of Ebonroc tank swap and dispatch-time anti-taunt-bounce checks | No duplicate swap system added |
| Flamegor | Normal tanking and generic enrage response | Explicit Tranquilizing Shot response to the live Frenzy aura |
| Chromaggus | Cover for both native variants of the chosen breaths; real Hourglass Sand use for Bronze | Explicit Frenzy dispel; affliction removal prioritizes players with more simultaneous afflictions, then tanks/low health, using native dispel types |
| Nefarian | Corrupted Healing admission/cast cancellation preserving safe priest spells; native phase/target eligibility | Engaged drakonid and bone-construct priorities; skip Victor's live immunity barrier; Veil removal and learned Fear Ward; melee rear-flank positioning |

## Behavior and safety

- Encounter actions are limited to map 469, live non-charmed bots and valid
  same-instance/phase objects. Add priority never initiates a pull. Explicit valid
  attack commands and raid marks retain targeting priority; protected Razorgore
  and barrier targets cannot be forced through the targeting safeguard.
- Razorgore phase admission reads native instance slot 0 and SPECIAL. It does not
  destroy eggs, control the orb, force boss flags, or advance the instance.
  This is a direct-target safeguard, not a guarantee against every incidental
  untargeted area effect near an uncharmed boss.
- DPS and available tanks focus adds; the active Razorgore/Nefarian tank is not
  reassigned to adds. These priorities are not a full split-room tank assignment.
- Firemaw uses the existing single-owner election, ready learned taunts, clean
  aura state, melee eligibility and dispatch-time rechecks. Native misses,
  cooldowns and immunity still apply. Five stacks is a conservative bot policy,
  not a changed boss mechanic or a claim of optimal tank timing.
- Support actions use ordinary learned-spell/range/mana/cooldown checks and
  reselect before casting. Emergency healing and danger movement remain higher
  priority. Bronze still requires an owned consumable; no item is fabricated.
- Vaelastrasz/Nefarian melee flank selection excludes healers, ranged and tanks.
  It chooses the nearer rear side and uses existing path/ground/LOS handling.
  Native chase receives a relative facing angle. Burning Adrenaline/cover holds
  continue to take precedence over this movement.
- No general class DPS rotation or warrior rage priority was changed.

## Remaining limitations and live checks

This is not a certified autonomous BWL clear. A player still needs to start and
lead encounters and operate Razorgore's orb/egg objective. No new automatic orb
operator, egg route, split-room kiting system, Onyxia Scale Cloak acquisition or
Nefarian hunter weapon-swap prediction is included. Class calls other than the
existing priest safeguard continue to use normal native/class behavior. There
is no predictive Wing Buffet tank rotation or guaranteed Chromaggus Time Lapse
backup-tank positioning. These require encounter testing and further bot work.

Live tests should cover Razorgore phase transitions/control breaks, add targeting
with raid marks and CC, Vael/Nef tail positioning and boss turns, Burning
Adrenaline with chasing, Broodlord range/LOS, Firemaw swap/stack resets, Ebonroc
swap regression, simultaneous Chromaggus afflictions/breath cover, Frenzy timing,
and Nefarian phase-three add pickup and class calls.

## Validation and rollout

Source-only native contracts checked all eight encounters and Victor Nefarius
against Classic, TBC and Wrath. Python regression syntax and source wiring were
checked. C++ fixture coverage was extended for protected phase targets, add
priorities, Broodlord spacing, Firemaw swap rules and movement arbitration.
**No C++ tests or core builds were run**, per the user's build preference.
The new support selection and flank behavior still require compilation/live tests.

Build **Classic, TBC and Wrath** from the updated local baselines, deploy the
resulting binaries, then restart each realm. **No SQL, client patch, or installer
change is required.** No live data, binaries, or running servers were modified.
