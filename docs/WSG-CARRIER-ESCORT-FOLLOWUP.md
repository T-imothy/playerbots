# Warsong carrier and escort follow-up

WSG carriers can be diverted by pursuit of an old enemy, and escorts travelling toward a carrier can overlook attacks on that carrier. Ordinary ranged targeting can also select a distant low-health enemy ahead of a nearby threat.

For independently controlled WSG bots:

- Automatic PvP and flag-carrier actions use the same eligible enemy selection. Enemy carriers take priority, followed by local threats to the allied carrier or bot, then ordinary enemies. Distance bands precede remaining health when choosing among otherwise equal candidates.
- Escorts recognize nearby attacks on their carrier. They must be within 30 yards of both the carrier and the visible attacker to treat this as local pressure. Merely selecting a player without attacking or casting does not establish pressure.
- Carriers travelling home or to a waiting position do not initiate attacks, chase an old enemy, charge toward it, or replace the home route with generic fleeing. Healing, positive buffs and movement abilities remain available. Native-legal instant control against a local pursuer can precede travel; offensive cast-time spells cannot.
- Carriers use the existing tunnel exit preference. A carrier already on a graveyard ledge completes the existing descent. Ordinary route preferences are retained for non-carriers and are not rewritten.
- Ordinary assist actions cannot undo the selected WSG opponent. Eligible candidate filtering still controls visibility, range, hostility and crowd-control exclusions.

The gates apply to actual WSG maps, including Wrath random-battleground queues. Direct player-controlled bots and gameplay outside WSG retain their previous decision paths. Native faction, flag, scoring, resurrection and encounter mechanics are unchanged.

## Verification and rollout

The production-body regression harness covers both factions, all three expansion modes, carrier selection, excluded opponents, escort leash/line-of-sight conditions, pursuit suppression, healing/escape exceptions, stable carrier exits, prior objective transitions and non-WSG/player-control boundaries. The companion PvP control regressions retain their native spell/target legality checks.

Native builds are required for Classic, TBC and Wrath. These checks do not establish live match quality: carrier escapes under pressure, escort positioning, terrain and flag transitions still need gameplay acceptance testing.

Only matching world-server binaries and symbols need deployment. No database or configuration change is required. A world-server restart activates the release.

Temporary `wsg-objective-followup` branches preserve this change for review. `wsg-before-objective-followup` branches preserve the preceding baseline revisions. Deleting review branches does not revert deployed files or baseline commits. Rollback requires restoring the recorded prior world binaries or reverting the release commits and rebuilding; later unrelated baseline work must be preserved.
