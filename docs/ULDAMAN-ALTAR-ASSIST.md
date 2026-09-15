# Uldaman altar assistance

When a master clicks the Altar of The Keepers (130511) or Altar of Archaedas
(133234), nearby party bots remember that specific interaction for up to 30
seconds. While the master channels at that altar, an idle bot moves into normal
interaction range and sends a normal game-object-use
request. The existing channel-hold action also recognizes Uldaman's 11206 altar
channel, so helpers do not immediately resume following or other idle actions.

The helper also discovers a real party member already channeling spell 11206
beside an active, incomplete altar. This recovers an invitation when no master
click event reached the bot, including a different party member initiating it
or an AI reset clearing the queued request. It never initiates an unused altar:
the channel, proximity, same group/instance and native use count must all match.
The nearby-object lookup runs only after finding that live party channel.

The shared noncombat default strategy enables this for every bot class. No
whisper command, encounter-state shortcut, direct boss activation, teleport,
or participant-count manipulation is involved. Bots do not initiate an altar
without a player starting its native ritual. Combat, death, group loss, map/instance changes,
expired requests, despawned objects and cancelled/completed channels prevent
assistance. The native object handler remains responsible for completion.

Classic and TBC data normally require three participants at each altar. Wrath
data normally requires one; the helper respects that data and does nothing
when extra participants are unnecessary. No database change is required.

Validation: the actual action is compiled into a native-interface fixture
covering both altars, invalid objects, movement, native interaction rules, participant
counts, channel state and stale requests. Existing ritual summoning fixtures
also cover the altar channel hold and remain valid across all three expansions.
This is not a claim of a completed live dungeon run.

2026-09-14 regression: the prior action fails the active-party-channel case when
no explicit Start event exists. The updated action passes that case and rejects
no channel, bot-only channels, completed/unused/owned altars and unrelated groups.
This proves coverage of the missing invitation path; it does not establish that
this was the precise path taken in the reported live failure.

The previous helper also required a center-point LOS ray before calling the
native click handler. Native HandleGameObjectUseOpcode in all three cores checks
interaction range, spawn state, object flags and CanUseNow, without that LOS
requirement. A collidable altar can obstruct its own center ray. The helper now
uses the native click rules once in range; movement/pathfinding still applies
while approaching. The blocked-ray fixture fails before this correction and
passes afterward. No native handler or encounter requirement was changed.

Range checks also match each core: Classic uses IsWithinDistInMap with its
interaction distance; TBC and Wrath use IsAtInteractDistance and model bounds.
This avoids rejecting a player already within a large altar's native click
bounds merely because its center is farther away. All three expansion variants
are compiled in the altar regression, including a model-bound interaction case.
