# Action dispatch regression fixes

## Changes

- Resolve the equipped ranged weapon before spell usefulness checks. Classic bow, gun and crossbow attacks no longer fail as generic Shoot; thrown weapons and weapon swaps use the same selection path.
- Refresh the pull action spell before usefulness checks, including actions created before their pull strategy or retained after a weapon change.
- Select a party member's actual paladin blessing before applying learned-spell checks. Normal and greater blessing dispatchers retain their existing selection rules.
- Refresh vehicle spell IDs before checking or casting abilities. Wrath vehicle actions can recover from an initially unavailable or changed ability ID through the existing spell-value cache; native vehicle cast checks remain authoritative.
- Preserve configured alternatives when a spell is unavailable or an action is under retry backoff. Unavailable abilities remain blocked, while their fallback actions receive independent validation. Ordinary unnecessary actions and stun-suppressed actions do not gain fallback behavior.
- Evaluate fresh real-player chat commands even when a previous attempt failed. Autonomous actions retain the retry limits. This does not promise a new chat explanation for every failure after an accepted action has started.

## Scope and validation

A targeted scan indexed 462 explicitly declared cast-derived action classes and reviewed dynamic spell setters, cached spell-ID consumers, specialized dispatchers, configured alternatives, and chat retry handling. This is not a complete encounter audit or a guarantee that unrelated systems contain no bugs.

Before/after C++ regressions reproduce the capability-order, cached vehicle ID, and command/fallback retry failures against production function bodies. The tests cover Classic, TBC and Wrath interfaces where applicable. Native builds and release receipts are recorded separately by the release process.

No database migration, configuration change, threat-number tuning or talent-balance change is required. The paused encounter-audit edits are excluded from this release.
