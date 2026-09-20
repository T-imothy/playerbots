# Avoid retaining empty aura lists during bot scans

The active Turtle core used its stable-reference aura getter even for boolean
`HasAuraType` checks. Each missing type could therefore create an empty list
retained until Unit destruction. Production showed over seven million aura
lists despite about 228 thousand actual aura effects. These counters measure
different objects, but the allocation path explains why empty buckets accumulate.

Core `HasAuraType` now reads the existing sparse bucket without materializing
it, as the CMaNGOS reference does. Six full-type scans in the active native bot
module first skip absent types: named aura checks/lookups, aura enumeration,
dispel checks, shaman purge and mount-speed lookup. Existing matching, ordering,
caster/stack/duration checks and actual spell effects are unchanged. These
queries run under their existing owner rules; no new threading model is added.

The public stable-reference getter is unchanged. This avoids invalidating aura
references held by other core callers. Existing lists are not forcibly freed;
the rebuilt server needs a restart to benefit from a fresh population.

Validation: MSVC native-fragment `AuraProbeMemoryTest` passes 2.31 million empty
probes without allocating buckets/pages, plus present/removed/reapplied aura and
stable-reference checks. Replacing the predicate with the previous production
body makes the test fail. Existing `Arch4StorageTest` also passes. No full server
build, live gameplay test, deployment or publication was performed.

No database or configuration changes. This addresses a confirmed retention
source, not a proven explanation for the entire RAM difference from Classic.
