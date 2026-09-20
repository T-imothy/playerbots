# Reduce measured allocation churn in Turtle-native bots

Scope: `modules/ManTechPlayerbots`. No changes to the CMaNGOS checkout, retired
TortoiseBots module, engine reset semantics, configuration or database.

## Evidence and limits

Production process 324's 60-second capture sampled 77,569 allocations at 1/1024,
with no allocation/site drops. Its before/after heap summaries, 202 seconds
apart, reported 3.6 MiB additional allocated memory versus 179.4 MiB additional
committed heap space. Heap scans themselves caused timing overhead; this is not
a representative performance benchmark. The difference includes reusable space
and allocator overhead, not an exact fragmentation measurement or proof of a
single leak. Pre-existing allocations are absent from the sampled stacks.

Auction mirroring, discovered-cell work and portal-distance calculations were
large allocation sites. Engine initialization appeared among survivors, but
comparison with the CMaNGOS reference found the same reset/rebuild behavior.
Its reset deletes triggers, multipliers and queued nodes. Skipping engine
initialization is therefore not justified by this capture.

## Local changes

- Auction mirroring clears/refills existing item vectors instead of destroying
  and regrowing every vector and map node each pass. It erases absent items and
  compacts vectors over 64 entries of capacity when utilization drops below a
  quarter, avoiding indefinite retention of past auction spikes.
- The read-only mirror pass walks native auction bounds under the same house
  lock instead of copying the pointer map first. Core bounds are ordered by
  auction ID, as was the former copied std::map. House ordering, buyout/count
  filtering and snapshot contents remain unchanged. Existing world-owner update
  scheduling and mirror-reader synchronization requirements remain unchanged.
- Scalar cross-map distance queries compute the minimum directly without a
  temporary vector of portal candidates. Same-map, missing/empty transfer sets,
  minimum selection and the existing unused `toMap` parameter retain semantics.

## Validation

`tests/allocation_churn_regression.py` compiles the actual two functions against
deterministic native-API fixtures with MSVC. It checks auction order/content,
changed prices, missing houses, invalid entries, removals, capacity contraction
and 200 steady-state refreshes with zero allocations. It compares 1,000 travel
queries in both flag modes against the previous algorithm, plus infinity/NaN
cases, and verifies no allocations in the new scalar query.

These are focused tests, not a full server build or runtime acceptance. The
changes target measured churn; no production RAM reduction is claimed yet.
Build Local Turtle, deploy/restart manually, then compare the same population
and activity over a similar duration. No publishing was performed by the agent.
