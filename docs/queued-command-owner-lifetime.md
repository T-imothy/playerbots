# Queued command recipient lifetime

Wrath production core `bbe9a3c7ddbbc7182f4507902aba55ecce0cd033`, with
Playerbots `4a72b831d2971c73c0f004cf4615608ca6dca47e`, crashed while processing
a queued `stance ?` command. The failing stack was `SetStanceAction::Execute`
→ `TellPlayer` → `TellPlayerNoFacing` → `Player::isRealPlayer`.

The matching full dump confirms that the incoming reaction's event still held
the invalid recipient address and that the bot's master was null. The memory
at that address no longer contained a Player object; its session field was
invalid. This is a stale queued recipient, not evidence of a fault in LFG
matchmaking. A player's use of LFG may have overlapped the incident, but the
dump does not establish that LFG caused the recipient to disappear.

Events, deferred chat commands, and external triggers formerly retained raw
Player pointers. Copying an Event preserved its pointer without preserving the
Player's lifetime. This design predates the enhancement work. The queue itself
returns an Event by value, so destroying the ActionBasket does not invalidate
that returned copy.

`EventOwner` captures the player's GUID and original address at submission.
Before use it resolves the GUID through ObjectAccessor, verifies the original
player instance is still registered, and verifies session attachment. The old
address is only compared, never dereferenced. Deferred commands and both action
engines reject expired recipients before dispatch; triggers retain the original
identity rather than converting a vanished requester into an autonomous event.
Events created without an owner continue to work normally.

The regression compiles the actual Event, EventOwner, ChatCommandHolder and
external trigger code against small core-interface doubles. AddressSanitizer
reproduces heap-use-after-free using the deployed implementation. The repaired
implementation covers live and copied owners, delayed chat, trigger-to-event
transfer, queued reactions, packet/GUID events, logout, replacement login,
detached sessions, and ownerless events. It also checks that both execution
engines and the chat queue apply the tested validity rule before dispatch.

This change does not add database migrations, settings, LFG features, or raid
mechanics. Realm startup tests and exact binary identities belong in the
release manifest. It does not constitute an end-to-end multiplayer LFG test
or a proof that all unrelated raw Player references are safe.
