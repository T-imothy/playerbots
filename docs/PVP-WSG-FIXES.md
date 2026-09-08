# PvP and Warsong Gulch fixes

These changes improve bot objectives and combat decisions. Native CMaNGOS flag pickup, return, capture, scoring, spell eligibility and battleground rules remain authoritative.

## Classic, TBC and Wrath

- Unflagged defenders can use the dedicated enemy-flag-carrier attack. The action no longer repeatedly selects an already selected carrier or diverts an allied carrier from its return task.
- WSG objectives distinguish flags at base, carried flags and dropped flags. Bots can travel toward distant drops and refresh moving carrier destinations.
- Independently controlled bots receive consistent jobs from their team's bot roster, with healer preference for support. Jobs are separate from route preference and do not reroll on each objective update or death.
- Carriers retain a stable waiting destination while their own flag is away and resume the capture route when it returns. Transient unavailable carrier/drop objects clear stale destinations.
- Non-carriers can continue toward their objective despite lingering combat when they are healthy and not under immediate pressure. They engage near the objective and retain self-defense. Direct player control is respected.
- WSG route branches propagate movement failure and can try the existing objective-directed waypoint graph. Repeated failure has a one-second action backoff instead of triggering random roaming.
- The Alliance second-floor exit correctly distinguishes approach from descent and selects the existing lower landing point.
- Carrier movement yields to urgent healing, dispels and appropriate mobility. Reaching the objective no longer repeatedly consumes movement actions or objective jump attempts. Routine map-buff detours no longer preempt every WSG objective movement request.
- WSG-only helpers check the actual battleground type before reading WSG state.
- Automatic unmarked crowd control can choose its first eligible enemy-player target. Native legality, marked targets and applicable damage protections remain in place.
- Sap routes casting and approach through its selected CC target and uses shared usefulness checks.
- Warlock automatic curse detection recognizes its own Curse of Exhaustion. This changes the bot's decision, not native aura stacking rules.
- Druid PvP kite roots consider nearby pursuit instead of requiring the enemy to use mana. Existing PvE selection remains intact.
- Battleground healing searches respect the configured heal search distance rather than silently halving it. Native spell range, line of sight and other cast checks still apply.

## Classic and TBC

- Shaman interrupt triggers and actions, including enemy-healer targeting, resolve to Earth Shock. Legacy action/strategy keys remain compatible. The obsolete fallback into a damage-shock chain was removed.

## Wrath

- Flag triggers and carrier values resolve random-battleground queues to their actual WSG/EotS map type.
- Shaman interrupts continue to use Wind Shear.
- Death Knight interrupts rank above routine damage/buffs. PvP can schedule Chains of Ice and Strangulate, including enemy-healer interrupts. Chains uses its snare target and Strangulate uses spell range rather than a melee approach requirement.

## Core integration

Each supported core exposes its existing WSG flag-state and dropped-flag-GUID getters publicly for read-only bot queries. No native battleground mechanics or data were changed. Each core pins the same playerbot release revision.

No database migration or new configuration line is required for this release. Deploy matching `mangosd.exe` and `mangosd.pdb`; activate with a realm restart.

## Verification

The regression harnesses compile production decision bodies against controlled native interfaces for all three expansion modes. They cover both factions, flag state changes, job consistency, moving and missing targets, pressure/recovery gates, route failure, the Alliance exit, random BG typing, CC legality, Sap, interrupts, curse recognition, roots and healing search limits.

Complete live battleground matches remain the runtime acceptance check. This release does not claim measured win-rate, DPS or CPU improvements.
