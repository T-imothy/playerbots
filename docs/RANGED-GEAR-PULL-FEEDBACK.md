# Ranged utility equipment and explicit pull feedback

Manual gear preparation could leave a warrior or rogue without a ranged weapon
when all scored candidates fell outside RandomGearMaxDiff. The production Classic
case was a level-33 warrior, a five-level limit, and ranged candidates requiring
levels 20 and 27. The existing level-gap gate dates to November 2023.

Allow older eligible bows, guns, crossbows and thrown weapons for warrior/rogue
ranged utility slots. Other slots/classes, item availability, native equip
requirements, blacklist and maximum item level checks remain enforced.
Manual gear entrypoints now initialize ammunition. Ammo selection also validates
type and required level so a bow-to-gun reroll cannot retain stocked arrows.

Explicit pull failure replies are private visible whispers even if ambient silent
mode or an intervening addon query would hide the reply. Existing security and
repeat suppression remain in place; autonomous pull failures stay silent.
The exact live cause of the originally missing reply was not captured.

Validation: production-method fixtures cover the observed level gap, unaffected
slots/classes, all manual gear entrypoints, ammo type/level changes, and explicit
pull reply options under Classic/TBC/Wrath defines. Native builds and deployment
verification are recorded in the release receipts. Live casting/pulling after
restart remains a player verification step.

After restarting the world server, issue the usual gear command again for affected
bots. Existing online equipment is not changed just by deploying a binary.
No database, configuration, addon or encounter-mechanic changes are part of this fix.
