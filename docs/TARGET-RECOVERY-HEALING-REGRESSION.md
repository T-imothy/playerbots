# Target recovery and healing decision turns

The September 9 recovery change (`d07d9dbefee38d3d927f2ba12d71c6743410df9b`)
counted any nonempty selection as completed combat cleanup. A successful unit
cast can leave its friendly recipient selected when the original selection was
empty. If no hostile replacement is available, the next recovery action clears
that friendly selection and returns success. The engine then ends that decision
turn before processing queued healing.

Only actual combat state (current AI combat target, bot victim, or pet victim),
or selecting a replacement, should make recovery consume a turn. Clearing the
selection alone still happens but now lets the engine evaluate the remaining
actions in the same turn. Existing enemy selection, CC protection, spell
interruption safeguards and combat cleanup remain in place.

This is shared target-recovery behavior, with no class condition. No healing
thresholds, rotations, spell range, party-target selection or movement policy
are changed. The initially considered range extension and cast-selection
restoration are excluded from this repair.

## Validation

`tests/target_recovery_healing_regression.py --history` compiles complete unit
cast and recovery method bodies with controlled interfaces for all three
expansion defines. With an injured ally and no available enemy replacement,
the earlier recovery code permits 12 heals in 12 decision turns; the introducing
commit permits 6 heals and consumes 6 cleanup-only turns. This correction again
permits 12 heals. Additional assertions preserve successful cleanup for actual
combat targets and attacks. These are decision-turn counts, not elapsed-time or
healing-throughput measurements.

Adjacent checks cover actual queue operations, party healing selection, five
healer specializations' trigger routing in PvE/raid/PvP, heal interruption, and
cast dispatch lifetime. Two existing test parsers were updated for the current
pull prerequisite guard and `defined(...)` preprocessing syntax.

A reported Classic priest stall motivated this investigation. This reproduction
establishes a regression in our recovery change, but does not establish that it
explains every reported delay or distant-healer incident. Normal behavior from
another healer is compatible with this conditional defect. Live gameplay must
still verify the reported incident after restart.
