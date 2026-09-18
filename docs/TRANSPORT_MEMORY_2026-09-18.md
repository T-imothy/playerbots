# Transport lookup allocation reduction

Active module: `modules/ManTechPlayerbots`, Turtle-native port.

`WorldPosition::getTransports` previously called `getGameObjectsNear(0, entry)`
for its elevator/tram fallback. That built and returned a vector of matching
spawn pointers, even though this caller only needs live transports. Repeated
movement checks could allocate large temporary lists when the entry is zero.

The fallback now visits spawns directly using the same ObjectMgr iterator.
It preserves entry filtering, unset-position behavior, map filtering, full
gameobject GUID construction and dynamic transport type checks. The native
boat lookup and fallback condition are unchanged. The map is resolved once;
a missing map now returns an empty result. No live pointer cache is added.

Existing periodic AI-value cleanup, unsupported-lookup handling and event
cache pruning were already present in this active module; they were not
missing and have not been duplicated.

Validation: `tests/transport_lookup_regression.py` extracts the production
function and compiles it with deterministic native API fixtures using MSVC.
It covers boat short-circuiting, elevators, map/entry filtering, ordinary and
unloaded objects, unset positions, repeated calls, object removal and no map.
This is a focused regression test, not a server build or gameplay test.

The change removes temporary vector allocations, not the spawn scan itself.
No RAM savings or resolution of long-session memory growth is established
until the rebuilt server is measured. No database/configuration change is
required. The disabled TortoiseBots donor edits are not included.
