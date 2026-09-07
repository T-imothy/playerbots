# Existing encounter and movement continuation (areas 3 and 7)

This continuation repairs existing behavior; it does not establish complete raid
strategies or successful full-instance traversal. Wider raids/dungeons (4–5),
release/promotion (6), dual spec and training dummies are outside this batch.

## Area 3: existing encounter decisions

- Netherspite only considers portals actually summoned by the engaged native
  boss. Both TBC and Wrath `DoSummonPortals` call `m_creature->SummonCreature`.
  Members whose group pointer no longer matches cannot reserve a beam.
- Exhaustion alone no longer sends an already-clear bot back toward a beam.
  A bot still inside a beam or carrying its stack aura can step out as before.
- The beam plan is recalculated immediately before executing movement, so a
  human taking over, exhaustion, or a role/group change can invalidate an old
  assignment. Strategy multipliers retain the normal cached read; they do not
  run a new grid/path search for every candidate action.
- At a valid assigned beam point, cancel a surviving chase instead of walking
  out of the beam. Preserve stationary casting when no relocation is needed.
- Extend the existing safe-position stop behavior to BWL Burning Adrenaline and
  Naxx burst/polarity positioning. Recheck current native threats and paths
  before stopping or moving. Release the hold when its native context expires.
  Stationary casts are preserved; movement-required reactions can interrupt.

The Netherspite changes are inactive in Classic. BWL/Naxx use each core's existing
native aura/phase policy. No aura removal, boss weakening, fabricated threat,
new teleport, LLM, shared worker or persistent data was added.

## Area 7: generic movement

- A transport-resume marker can outlive its cached route. Require both dock and
  exit before reading them, and check again after special-movement selection
  trims a copied route. Invalid routes drop the stale resume marker without
  submitting a transport move; valid waiting/disembark behavior remains.
- Include destination height in failed-path retry cells. Two destinations on
  different floors with the same X/Y no longer share the same failure key.
  Preserve the existing eight-yard cell size, retry interval and generation/
  instance invalidation, including copy/reset semantics.

## Verification

Actual-source executable regressions cover stale group references, portal
ownership, exhaustion away from and inside beams, changes between selection and
execution, invalid paths, cast-preserving safe stops, empty/one-point/trimmed
transport routes, and vertically distinct retry requests. The new group-roster,
empty-route and vertical retry assertions failed against the pre-fix source.
The complete regression run has 90 runners. Native compilation and dev startup/
load observations are recorded separately in the task report.

Remaining area-3 work includes the full mechanics/assignments and live raid runs
in the encounter register. Remaining area-7 work includes actual dungeon geometry,
boats/vehicles, changing hazards and reproducible traversal/load scenarios.
Passing controlled fixtures or an idle-world sample cannot close those items.
