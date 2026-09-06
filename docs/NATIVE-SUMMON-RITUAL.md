# Explicit warlock summons use the native ritual

`cast summon Name` asks the warlock to start its learned spell 698 normally.
It does not create a summon packet or move the recipient itself. The core checks
mana, reagents, cooldowns and casting rules. Nearby grouped bots approach and
click the native ritual through `HandleGameObjectUseOpcode`; human helpers must
click it themselves. The core counts participants, ends their channels, casts
the completion spell and sends the ordinary accept/decline request. Bot targets
retain the existing normal summon-response handler.

The bare `summon` convenience command is separate: it brings bots to an allowed
inn/stone location and neither spends nor resets anyone's hearthstone cooldown.

## Verified native expansion chains

| Core | Native chain |
|---|---|
| Classic | 698 -> ritual GO 36727, three participants including caster -> 7720 summon request |
| TBC | 698 -> native replacement 46546 -> GO 36727 -> 7720 |
| Wrath | 698 -> GO 194108, three participants -> core replacement 62330/61993 -> portal 194097; a portal click starts 61994 -> GO 179944, two participants -> 7720 |

Wrath retains one short-lived request containing target/requester GUIDs and
map/instance identity for the second stage. No stored Player/GameObject pointers
or teleport coordinates survive an action. The request expires, is cleared on
invalid group/lifecycle/map state and is consumed before the portal click. The
portal is found by native grid lookup and must be live, local, owned by the
warlock, entry 194097 and created by 61993. Type-23 objects created by native
EffectTransmitted are not added to Unit's ordinary owned-object list.

The shared `default` strategy schedules assistance for every class; the old
NonCombatStrategy base is not common to all modern class strategies. A hold
action preserves native summoning casts/channels without rooting the bot,
extending the spell, faking participant counts or suppressing combat reactions.
No Ritual of Doom assistance is added.

## Validation and remaining play checks

Actual-source C++ fixtures cover all three compilation gates, native cast
rejection, helpers, live object/owner/map checks, distance/path submission,
channel holding, Wrath portal ownership, expiry, invalidation and one-shot use.
The parser suite verifies neither humans nor bots are immediately transported.
These tests do not run the real spell engine or establish client success.

In dev, test each expansion with a learned warlock, two nearby helpers and a
distant grouped player: correct prompt and destination, decline then retry,
missing shard, movement interruption, helper departure and logout. In Wrath,
also reuse the portal and let it expire. Test the bare convenience command
separately with an existing hearthstone cooldown; its value must remain unchanged.

No SQL migration, new log or scan thread is required. The pending request is
functional state, not diagnostic instrumentation to remove later.
