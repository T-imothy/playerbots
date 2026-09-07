# Empty and stale encounter target lists

A follow-up to the Maexxna finding reviewed native boss target-list truncation
and first-element access. This is a source and regression audit, not a complete
implementation of the encounters' group strategies.

## Corrections

- **Renataki, all three cores:** Thousand Blades enlarged its secondary-target
  vector to nine even when fewer eligible players remained. It now only
  truncates lists larger than nine. This preserves the initial target exclusion,
  shuffle, maximum of nine secondary targets, effect-index gate and triggered-
  cast recursion guard. It avoids additional casts with null target arguments;
  those calls were not themselves a reproduced server crash.
- **Nazan/Vazruden, TBC and Wrath:** the facing spell script called `front()` on
  the native threat list without checking whether it was empty. It now requires
  a caster, a nonempty threat list, a reference and its target before changing
  facing. Valid highest-threat facing remains unchanged. Missing references
  produce no facing update.
- **Thorim, Wrath:** the closest-ground-helper query checked the stored GUID
  list before resolving it, but every referenced helper could have despawned.
  It now checks the resolved creature list before sorting and reading its first
  element. Surviving helpers still use the existing distance ordering.

`encounter_target_list_regression.py` executes the actual native methods in
each applicable core. Renataki cases cover zero through fifteen secondary
targets, unique targets, exclusion of the primary target, and recursion/effect
gates. Facing cases cover empty lists, null references, missing reference
targets, missing caster and valid facing. Thorim cases cover an empty GUID list,
all GUIDs missing, partial despawns and preserved nearest-helper selection.

Separate before-fix runs reproduce each defect. Checked list fixtures make
invalid `front()` calls fail deterministically instead of relying on undefined
behavior to crash. After-fix fixtures pass in all three core variants.

Other reviewed first-element accesses in Gluth, Mimiron and Kel'Thuzad already
guard their populated selection lists. They were not changed. Fixed-size GUID
storage and truncation of populated encounter-entry pools are separate uses of
`resize()` and are not automatically defects.

No database migration, new setting, production change or baseline promotion is
part of this batch. Exact builds and runtime status are in the task report.
