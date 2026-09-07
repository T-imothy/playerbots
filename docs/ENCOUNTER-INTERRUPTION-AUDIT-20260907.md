# Encounter interruption follow-up

Follow-up to [selection/rescue audit](RAID-DUNGEON-SELECTION-RESCUE-20260907.md).
These changes affect existing bot combat/cast handling; they do not introduce a
new encounter strategy or the separately discussed priest heal-target ranking.

## Wrath interruption packet layout

All three native `Spell::SendInterrupted` implementations send a packed caster
GUID in `SMSG_SPELL_FAILURE`. Classic/TBC then send the spell ID and result.
Wrath inserts an additional one-byte cast counter before the spell ID. The bot
handler previously read the Classic/TBC layout in every build, reporting the
wrong interrupted ID on Wrath. Consequently `SpellInterrupted` can fail to match
the tracked cast and leave its previous scheduling delay in place.

The Wrath branch now consumes that byte before reading the ID. Classic/TBC keep
their wire layout. Packets for another caster and the secondary failure opcode
retain their previous behavior. No protocol or core packet writer is changed.

`spell_failure_packet_regression.py` compiles each core's actual packet writer
and the bot's actual failure-handler block together. It covers sparse/full packed
GUID shapes, multiple spell IDs, cast counters 0/1/255, self/other casters and the
secondary opcode. Before the fix, Classic and TBC pass while Wrath reports the
wrong ID. After the fix all three pass. This is a reproduced protocol mismatch,
not an inferred explanation for a particular production healing report.

## Common cancellation metadata lifetime

`PlayerbotAI::InterruptSpell` now saves the spell ID before calling native
cancellation. Native cancellation can invoke aura and AI callbacks and release
the current-slot reference; the caller no longer reads the spell object across
that boundary. Its existing melee/autorepeat options, channel exclusion and
interruptibility decisions are unchanged.

`interrupt_spell_lifetime_regression.py` compiles the actual helper and invalidates
metadata at the controlled cancellation boundary. The previous helper reads it
after cancellation; the corrected helper reports the saved ID. This is a lifetime
hardening test, not a claim of a reproduced native production use-after-free.

## Scope and validation

The follow-up source review also checked the Nefarian corrupted-healing helper,
the native interruption notification, the generic cancel action and the existing
damage/reflection holds. The ordinary native failure notification is the relevant
path for Nefarian's selective cancellation; the Wrath parser fix repairs that
notification without adding a duplicate encounter-specific scheduling rule.

The full regression count is now 94 runners. Final execution results, native
builds, symbol identities and isolated localhost startup checks are recorded in
the final task artifact. No SQL, configuration, new persistent state or automatic
production deployment is required by this follow-up. The broader new-system and
live-encounter gaps in the mechanic register remain explicit.
