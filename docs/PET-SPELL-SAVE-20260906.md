# Pet spell persistence follow-up

During the local development soak, TBC logged duplicate `pet_spell` primary keys
for pet/spell pairs 118145/6307 and 121159/27269. The affected records belong to
warlock imps. This observation is not a production diagnosis or proof that the
Playerbots enhancements introduced the underlying race.

The native cores queue SavePetToDB transactions asynchronously, while loading pet
spells uses the synchronous query connection. Summon replacement can unsummon an
old pet and immediately load it again. If a newly learned spell's save is still
queued, the reload can miss that row and relearn the spell as PETSPELL_NEW. When
the old save commits before the next save, the unconditional new-spell INSERT
collides with the existing primary key. A controlled regression reproduces this
sequence with each core's actual _SaveSpells implementation. The logs alone do
not identify the exact scheduling of the two observed incidents.

All three cores now save PETSPELL_NEW using the same exact-key DELETE followed
by INSERT already used for PETSPELL_CHANGED. Both statements remain inside the
existing pet-save transaction. This preserves the latest saved active/autocast
state and avoids a duplicate-key failure for a stale NEW classification. Only
that pet/spell row is replaced; unrelated spells/pets are untouched. Unchanged
spells remain write-free, removed spells are deleted, and family passives remain
excluded. The tradeoff is one extra exact-key DELETE for each newly saved spell.

`pet_spell_persistence_regression.py --before` fails on the previous code. The
current test passes for Classic, TBC and Wrath and covers queued saves, stale
reloads, active-state updates, repeat saves, removal and family-passive exclusion.
The fixture models FIFO database writes and a primary key; it does not prove
every pet lifecycle is correct or measure production database performance.

No schema change, data repair or new configuration setting is required. The
existing primary key remains in place. Production and ManTech baseline branches
are outside this local enhancement checkpoint.
