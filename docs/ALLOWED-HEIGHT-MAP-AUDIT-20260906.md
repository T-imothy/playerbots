# Native allowed-height map context

All three cores' `Unit::UpdateAllowedPositionZ(x, y, z, atMap)` accepted a map
override but queried non-flying ground height through `GetMap()`. Swimming then
combined that source-map ground height with water from `atMap`. Flying already
used the requested map. The non-flying branch now uses `atMap` too.

The native regression gives the current map ground height 40 and the requested
map height 100. Before the fix, the method clamps Z to the wrong ground. The
corrected method passes in Classic, TBC and Wrath. Additional cases preserve
default-map calls, swimming between floor and surface, water walking, flying,
invalid-height handling and Wrath phase/hover behavior.

Native call sites passing a map include `WorldObject::GetNearPoint` placement
and DB-script dynamic movement near a target. This is a correction to the
existing map-override contract, not a change to path generation or map data.
No new DB rows or config lines are required.

This does not explain the sampled TBC bot's transient 0.95-yard terrain offset:
that sample was on the same map. Its cause remains unestablished. The preceding
c42c2610 build produced live nearby walking paths in all three dev realms, but
those calculations did not prove full route traversal or encounter clears.
