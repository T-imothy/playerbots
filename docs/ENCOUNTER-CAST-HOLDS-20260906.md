# Mandokir and Anzu casting safeguards

These shared policy changes apply to automated bot decisions. They do not alter
native boss spells, aura lifetimes, player control, database rows or configs.

## Mandokir: Threatening Gaze

In all three cores, native `boss_mandokirAI::ReceiveAIEvent` saves the watched
player's threat when aura 24314 starts and compares it when the aura ends.
Increased threat triggers the punishment; leaving line of sight can summon the
player back. The bot therefore pauses its own melee and threat-generating casts
while that aura's actual caster is a live, engaged Mandokir (11382) in its map
309 instance. Movement remains available. The policy does not impose an arbitrary
distance cutoff on a player the boss is still watching.

Helpful spells carrying native NO_THREAT, NO_INITIAL_THREAT or NO_HELPFUL_THREAT
flags remain available because native `HostileRefManager::threatAssist` excludes
them. Harmful NO_THREAT spells remain blocked: native `ThreatManager::addThreat`
can still add threat to an existing reference. Pets do not inherit the owner's
personal gaze hold. Existing interruptible unsafe casts, channels, autorepeat and
queued melee are stopped; each dispatch and interruption rechecks the condition.

## Anzu: Spell Bomb

In TBC and Wrath, aura 40303 from Anzu (23035) in map 556 triggers payload 40305.
Local spell data gives the aura proc mask 0x55500; the payload burns mana,
interrupts and stuns. The native spell proc classifier excludes ordinary melee
ability hits and ranged auto attacks, including wands. It includes spell casts,
healing and harmful periodic ticks. The bot therefore holds qualifying casts,
including healing, while allowing plain melee, melee abilities without secondary
effects, and ordinary ranged auto attacks. Direct casts suppressing caster procs
retain that native exception. Owner Spell Bomb does not stop pet casts.

Melee abilities with periodic damage, or spells with triggered payloads, are
withheld conservatively: their secondary effects can use different proc masks.
The policy does not remove existing damage-over-time effects, recall launched
missiles or suppress native passive procs. It is not a complete Anzu strategy;
brood targeting and bird-spirit healing assignments remain separate mechanics.

## Validation and boundaries

`encounter_damage_pause_regression.py` compiles and executes the actual shared
policy methods for all three eras with controlled native-shaped objects. Cases
cover target/caster identity, world and instance/phase membership, aura expiry,
death, teleport, charmed and real-player exclusions, personal versus pet casts,
helpful threat flags, melee/ranged classification, secondary effects in every
effect slot, and cancellation of existing spell slots. Native builds additionally
check integration against each core's real APIs. These tests do not establish
live encounter clears or guarantee that already-applied periodic effects cannot
trigger punishment.
