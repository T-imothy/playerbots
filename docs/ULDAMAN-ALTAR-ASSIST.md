# Uldaman altar assistance

When a master clicks the Altar of The Keepers (130511) or Altar of Archaedas
(133234), nearby party bots remember that specific interaction for up to 30
seconds. While the master channels at that altar, an idle bot moves into normal
interaction range, checks line of sight, and sends a normal game-object-use
request. The existing channel-hold action also recognizes Uldaman's 11206 altar
channel, so helpers do not immediately resume following or other idle actions.

The shared noncombat default strategy enables this for every bot class. No
whisper command, encounter-state shortcut, direct boss activation, teleport,
or participant-count manipulation is involved. Bots do not initiate an altar
without the master's click. Combat, death, group loss, map/instance changes,
expired requests, despawned objects and cancelled/completed channels prevent
assistance. The native object handler remains responsible for completion.

Classic and TBC data normally require three participants at each altar. Wrath
data normally requires one; the helper respects that data and does nothing
when extra participants are unnecessary. No database change is required.

Validation: the actual action is compiled into a native-interface fixture
covering both altars, invalid objects, movement, line of sight, participant
counts, channel state and stale requests. Existing ritual summoning fixtures
also cover the altar channel hold and remain valid across all three expansions.
This is not a claim of a completed live dungeon run.
