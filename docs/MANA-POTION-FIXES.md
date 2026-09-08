# Mana-potion recovery fixes

Applies to Classic, TBC and Wrath, through the shared playerbot code.

- Low-mana recovery can reach the mana-potion alternative when Dark Rune is unsuitable (including low health, mage restrictions or a skipped rune spell). The reaction engine now honors the existing explicit alternative-action contract, matching the combat engine.
- Item feasibility checks include native item eligibility. An underlevel rune can no longer hide an eligible potion and then fail at execution.
- Potion searches distinguish mana restoration from rage and energy restoration, and continue past an invalid item spell slot.
- Potion-cache level bands include potions unlocked within the band, avoid unsigned level underflow, and filter the selection against the bot's actual level. This also corrects the shared healing-potion level selection.
- Mana is rechecked before a queued potion action so recovered mana and non-mana classes do not cause wasteful use.

Native cooldown, item ownership/cheat, combat and arena restrictions remain in effect. The potions strategy must be enabled. No production database or configuration migration is required.

Regression tests compile the actual reaction-selection, item-eligibility, potion-visitor and cache functions with controlled game interfaces in all three expansion modes. Coverage includes all seven mana-using classes, low-health and underlevel rune fallback, missing items, cooldowns, level boundaries, restored mana, stun and arena restrictions, and unchanged ordinary-action fallback behavior. These tests are not a live-combat reproduction of the reported priest.

The rune restrictions and missing native item precheck predate the recent class audits. The reaction engine had not adopted the explicit fallback contract already supported by the combat engine.
