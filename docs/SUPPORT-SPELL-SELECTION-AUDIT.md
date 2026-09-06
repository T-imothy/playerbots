# Support-spell dispatch audit

2026-09-06; all three testing expansions. No new spell, configuration, log,
database state or cooldown bypass is introduced.

## Paladin aura selection

The existing `NoPaladinAuraTrigger` already checks that the bot has no owned
aura. It is **not** evidence of a continual normal aura-flipping loop. However,
the action declared itself unconditionally possible/useful and did not repeat
the owned-aura check. A queued/direct invocation could therefore replace a
valid aura after the trigger was evaluated. Its successful dispatch also used
`SetDuration(1.0f)`: the duration API takes milliseconds, not seconds, and an
already-declared normal duration variable was unused.

Trigger, feasibility and execution now share one existing-policy selector. It
checks native world/life/control/teleport and learned-spell availability, keeps
the bot's existing aura, and chooses a learned aura missing from nearby coverage
in the same priority order. Classic excludes Crusader Aura; Wrath excludes the
removed Sanctity Aura. Explicit named aura actions and existing specialization
priorities are unchanged. Actual cast admission remains the normal Playerbot/
core path; successful dispatch uses its reported duration. The existing explicit
attack-speed cheat retains the generic one-millisecond exception.

## Mage food/water

The special conjure-item loop iterated the whole native spell map and chose the
highest usable item's spell ID, but skipped neither removed nor disabled entries.
Those entries can remain in the map pending save/cleanup. It could keep choosing
an unusable rank even while a lower usable rank exists. The loop now uses the
native `Player::HasSpell` predicate and skips passive metadata before choosing.
Item eligibility, item existence, highest-ID ordering and normal cast admission
are otherwise unchanged. This is not asserted to explain any historical unknown
spell-zero log, whose exact origin was not established.

`support_spell_selection_regression.py` compiles the actual selector, action,
trigger, conjure branch and each core's actual `Player::HasSpell` predicate.
Cases include stale/direct dispatch, existing owned/other auras, no learned aura,
cooldown/cast failure, native duration and cheat exception, expansion exclusions,
removed/disabled/passive conjure ranks, invalid/unusable items and no eligible
rank. All three modes pass. Runtime group coverage and actual spellcasts remain
in-client test items; no CPU/RAM percentage is claimed.
