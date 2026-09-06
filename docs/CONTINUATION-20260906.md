# September 6 continuation — testing branch only

The ManTech main branches remain the rollback source baselines. This work does
not authorize a production deployment or imply complete dungeon/raid coverage.

## Changes since 07b5e401

- Healer candidate selection bounds incoming-damage forecasts, prevents health
  underflow, removes duplicate candidates and calculates each forecast once per
  selection. Pet healing checks the pet's incoming casts rather than its owner's.
  Finished casts and invalid life/map/phase/teleport targets are rejected. Native
  spell admission and existing healer distribution remain in use.
- Naxxramas charge separation now follows native Thaddius auras 28059/28084 and
  their damage payloads 28062/28085. Same-charge players may remain together;
  opposite-charge and uncharged players are separated with bounded native paths.
  The current boss tank is left planted while other bots separate. Current aura,
  group, map/phase and destination checks apply again before movement. No charge
  or damage buff is fabricated/removed. This does not yet provide phase-one add
  assignments, platform jumping or optimized same-charge stacking positions.
- Molten Core movement now rechecks the live combined danger areas immediately
  before moving, preventing a cached Living Bomb destination from becoming unsafe
  after another member moves. Teleporting, charmed and departed group members do
  not keep a stale separation decision alive. Native height adjustment must also
  leave the destination outside those danger areas. A malformed current-cast
  record with no spell metadata is safely ignored.

## Verification boundaries

Focused actual-source healer, Naxxramas value/action/multiplier and Molten Core
value/action tests pass in Classic, TBC and Wrath compilation modes. Full suite,
exact-revision native builds and release artifacts are recorded in the final
package manifest separately; an uncommitted source edit is not an installed build.

Native Thaddius source was checked in Classic/TBC eastern_kingdoms/naxxramas and
Wrath northrend/naxxramas: charge damage excludes recipients with the same charge,
including the fact that an uncharged recipient is not immune. Radius lookup uses
each running core's native spell data. Human movement and native auras are untouched.

## Still required

The broader boss-by-boss audit and remaining routines in COMBAT-REWORK-STATUS.md
remain open. In-client tests must check charged/uncharged players, polarity
changes, the active tank, blocked paths, Geddon bomb carriers changing position,
post-kill aura lifetime, actual healing and normal dungeon/raid transitions.
Controlled tests are not evidence of a completed raid clear.
