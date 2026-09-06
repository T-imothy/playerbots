# Native Soul Leech and falling corrections

## Wrath Soul Leech

The dev soak recorded 34 unknown-spell-0 messages, in pairs, from four warlocks.
All four characters have Improved Soul Leech talent 1889. Native `SoulLeech::OnProc`
selected mana-return IDs using the ordinary Soul Leech aura ID, but its switch
only accepted Improved Soul Leech rank IDs 54117/54118. Both IDs therefore stayed
zero. The controlled regression reproduces that invalid dispatch before the fix.
The file was unchanged between the ManTech Wrath baseline and the audited core
HEAD before this correction; this is not evidence that the new bot code introduced
the native mismatch.

The switch now uses the actual Improved Soul Leech aura's rank. Rank one retains
54300/54607 and rank two retains 59117/59118. Replenishment 57669 retains its native
chance, captured before triggered casts can change aura state. An unexpected rank
retains the base heal and does not dispatch zero spell IDs. No existing proc aura
is read after the triggered base heal. The regression covers all ordinary ranks,
both improved ranks, the chance succeeding/failing, missing/unknown talent ranks,
nonplayers, and aura invalidation during triggered casts.

## Native falling, all three cores

`MotionMaster::MoveFall` used an absolute height difference, accepting detected
surfaces above the unit as falling destinations. Native falling timestamps use
downward height loss; an upward request can produce the zero-duration spline
warning seen during the TBC soak. The log did not identify the mover or its path,
so the exact observed incidents cannot be assigned to this path from logs alone.
The native request regression independently reproduces the invalid upward fall.

Fall requests now reject nonfinite coordinates/heights and require a downward
height difference, retaining the existing half-yard minimum. A second check in
`MoveSplineInit::Launch` runs after the actual current spline position replaces
the first vertex: it stops a queued fall whose destination is now above, level
with, or less than 0.01 yard below the mover. Normal nonfalling movement is
unchanged. Valid falling retains its destination and completion callback data.
The existing native diagnostic remains enabled.

Tests execute each core's actual request method and final fall-admission block,
covering invalid terrain results, upward/same-level/short/valid drops, Wrath phase
selection, stale positions at dispatch, and preservation of normal movement.
These guards do not repair terrain meshes or teleport units out of geometry.

Both fixes change native code; no schema migration, manual database repair,
configuration addition or production deployment is part of this audit step.
