# Soccothrates charge marker validation

Soccothrates previously saved charge coordinates only when the summoned marker
arrived, then used those coordinates after the targeting spell reported success.
A successful cast with a failed creature allocation could therefore use old or
uninitialized coordinates for the Felfire line.

The TBC and Wrath scripts now retain the current charge marker's GUID and obtain
its live position before placing each Felfire creature. Reset and each Knock Away
clear the preceding marker. Missing targets, rejected targeting casts or absent
markers retry the setup after 500 ms. A rejected Line Up cast retries against the
existing marker, avoiding duplicate summons. Dead or out-of-combat callbacks do
not start a new setup. Felfire placement requires the expected creature entry and
keeps the existing seven-segment geometry within the boss-to-marker line.

Native spell data confirms targeting spell 36038 is instant and summons entry
21030; Line Up 35770 targets entry 20978. No spell, creature template, SQL or
configuration changes are required.

`soccothrates_marker_regression.py` executes the native methods with missing
targets, cast failures, 100 failed allocations, stale markers across Knock Away,
retry without duplicate summons, null/wrong targets, line coordinates and reset
or combat exit. Both core fixtures pass. Development native builds are recorded
separately. No production deployment or live encounter clear is claimed.
