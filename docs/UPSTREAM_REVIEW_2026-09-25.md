# Upstream playerbots review — 2026-09-25

Reviewed cmangos/playerbots master through 00e8f731, from our shared ancestor
4120aa9d. This is a selective backport, not a wholesale upstream merge.

## Included

- 01635cdc + b8fcbc4c: guard zone reads for detached/mid-teleport bots during
  random teleport placement and administrative statistics/listing; report bots
  outside the world separately from zone counts.
- da312a9f: do not schedule auction-bot background work while its config is disabled
  or has not enabled it yet.
- a2ae599e: offered resurrection outranks autonomous corpse recovery/release.
- e4b58883: retain a resurrection packet for retry when its trigger is occupied.
- 9b1049f4: allow conjured consumables through the zero-sale-price trade check.

All apply to the shared Classic/TBC/Wrath source. Existing trade eligibility,
resurrection validity checks, and map lifecycle replacements remain active.

## Already present

- Elevator travel/node fixes dd99cc21, 06ec55b8, and 51d246db are ancestors of our
  baseline. In particular, Gnomeregan's overhead plunger is excluded as a lift.
- The empty quest-reward selection guard from 8ef9193d is already implemented.
- Paladin blessing ownership protection from 34d4aded originated in our fork.

## Not included in this batch

- b3995619 changes external-event retention across Engine/ReactionEngine. Our
  engine has queue expiry, retry suppression and event-owner lifetime changes;
  this needs dedicated queue/reset/expiry integration tests before adoption.
  The two included resurrection changes improve priority and packet admission,
  but do not claim to solve every external-event loss case.
- 37bf15e7/d4dda549/5d9a61cd/00e8f731 change cooldown use on dungeon trash versus
  bosses. These are combat policy changes, and the final null guard fixes the
  newly introduced code. Our existing boost behavior has not been replaced.
- 9bf2e483 changes enhancement shield policy; shield preference is not a universal
  stability fix and needs expansion/spec/talent-specific evaluation.
- 4cf72bae broadens filtering in a shared nearby-hostile helper, beyond looting.
  Neutral-but-attackable encounter targets need coverage before adoption.
- Upstream test-harness changes and the auction config installer change are not
  imported; our build/deployment and regression infrastructure is customized.

## Validation and deployment

Reviewed diff and native Item::IsConjuredConsumable API in all three cores.
All three lifecycle SHA guards are updated for the reviewed PlayerbotAI.cpp
resurrection registration change; the lifecycle replacement code is unchanged.
CMake configuration is checked for each core. No game server binary is compiled
or deployed in this batch, and no live database is modified.

After publishing the shared commit and updating all three core pins, rebuild
Classic, TBC and Wrath locally, deploy their matching exe/PDB files, and restart
those realms. No SQL or client patch is required. Live checks still needed:
accept resurrection during corpse recovery, trade conjured food/water, and run
bot statistics while bots are teleporting.
