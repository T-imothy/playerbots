# Triggered ground damage and Nexus follow-up

Development audit changes; not a deployment or a live encounter-clear claim.

## Shared ground hazards

The generic collector previously recognized periodic damage, percentage damage
and leech, but missed a persistent area aura that periodically triggers a separate
self-damage spell. It now checks one payload hop, requiring native self-targeted
school damage. Native area eligibility, hostility, radius, lifetime and map gates
remain in force. It does not recurse through arbitrary scripts or classify
healing, summons, control effects or Flame Wreath's dummy as damage.

The local TBC and Wrath spell data contain six qualifying parent spells:
31943 Doomfire, 35278 Raging Flames, 35769 Felfire and 40253/40255/40263 Molten
Flame. This detects remaining dynamic trails as well as the separately supported
moving actors. Classic has no qualifying chain in the queried development data;
its collector remains compatible with the same shared implementation.

`encounter_runtime_regression.py` executes the actual predicate for all three
core variants, including missing payloads, alternate effect slots, wrong targets,
harmless effects and native attack rejection. The Flame Wreath movement hold
still takes precedence through existing combat/reaction multipliers.

## Ormorok

The normal spell list 2679401 casts 47958. The native four-direction ScriptEffect
already implements that spell, but the local development database has bindings
only for heroic 57082/57083. Prepared Wrath database update
`5878_ormorok_normal_spikes.sql` adds the missing normal binding. The native
counter reset now includes 47958, so later normal waves can grow after the first
wave reaches the existing cap. Normal and heroic timing, directions and cap are
unchanged.

On heroic difficulty, autonomous DPS can prioritize Ormorok's own living
Crystalline Tanglers (32665) carrying their native proc aura 61555. Telestra's
clones still require her split aura. Normal difficulty, foreign summons, protected
crowd control, tank/healer roles and explicit targets retain their safeguards.

`ormorok_spikes_regression.py` executes 100 cycles for each normal/heroic cast and
their native four-direction dispatch. `summon_objectives_regression.py` tests
Tangler ownership, difficulty, aura, lifecycle, phase and ambiguity alongside
existing objectives. The migration was applied twice to a session-local temporary
table and preserved heroic and unrelated rows. It has not been applied to a
persistent development or production table.

## Cached hazard lifecycle follow-up

An executable reproduction showed that a stored object hazard could survive a
same-map phase change. TBC and Wrath have native phase masks; Classic's native
membership check still verifies the live map instance. The shared cache now uses
that native membership check and rejects unspawned gameobjects and dead units.
The initial hazard triggers apply the same lifecycle checks, rather than raising
an escape reaction from an obsolete cached source. The creature trigger's
existing exception for its current victim is preserved.

`encounter_runtime_regression.py` covers cache validity and overlapping/nonoverlapping
phase masks. `hazard_trigger_lifecycle_regression.py` executes the actual trigger
bodies across all three core variants. The remaining lifetime of an active
dynamic ground spell is preserved; death of its caster alone is not substituted
for native dynamic-object removal.

## Verification

The ground-chain/Nexus checkpoint passed all three native builds and the full
159-runner suite. The subsequent lifecycle change has focused cache/trigger tests;
its final native build and affected movement verification are recorded separately
in the task checkpoint. The runner inventory is now 160, not a claim of a new
full 160-runner execution.

## Limits

Evidence is from source, local spell data and executable fixtures. Ground escape
routes, simultaneous spike waves, actual heroic Tangler pulls and mushroom
positioning in Amanitar still require gameplay validation. Amanitar's Potent
Fungus/Mini interaction was inspected but no unverified aura removal or mushroom
target rule was added. The full encounter mechanic register remains open.
