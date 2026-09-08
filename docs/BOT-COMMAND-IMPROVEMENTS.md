# Loot preferences and bot status commands

These commands are available in Classic, TBC and Wrath. No addon update,
configuration option or database schema migration is required. The new
automatic roll policies require the matching core's read-only vote eligibility
accessor; build the shared Playerbots changes together with that core change.

## Automatic group-loot preference

Whisper a controlled bot:

```text
roll policy ?
roll policy auto
roll policy pass
roll policy greed
roll policy need
```

The default is `auto`, preserving the existing item-usage decision. `pass`
passes automatic votes, including when bags are full. `greed` chooses Greed
when allowed, otherwise Pass. `need` chooses Need when allowed, otherwise Greed,
then Pass. The original roll's eligibility, loot method and item restrictions
are checked; already-voted, expired and ineligible rolls cannot be overridden
by this policy.

The policy applies to subsequent automatic votes in combat and out of combat,
including the existing automatic response when the master rolls. Changing it
does not revise a vote already submitted. Existing one-time `roll need`,
`roll greed`, `roll pass` and `roll auto` commands retain their existing meaning.
The feature does not change corpse looting, FFA/master-loot rules, or the `loot`
strategy. Only `auto` chooses Disenchant through the existing Wrath item-usage
logic; the new `greed` policy specifically chooses Greed.

The real-player master or a GM allowed to control the bot can change/query its
policy. A free bot defaults to `auto` until an authorized requester changes it.
Preferences belong to each bot and survive logout and restart. An explicitly
changed preference remains that bot's preference after leaving a group; reset
it with `roll policy auto` when appropriate.

Storage uses the existing character database `ai_playerbot_db_store` table,
reserved preset `__roll_policy`, key `mode`. It is independent of strategy
presets, hidden from `list ai`, and protected from strategy preset save/load/
reset operations. A policy change does not save temporary combat strategies.
An ordinary value reset reloads the saved policy; it does not erase it.
Invalid command modes leave the saved preference unchanged; invalid stored
modes fall back to `auto`. Persistence uses the existing database write queue.

## Pull feedback

Explicit `pull` and `pull rti` failures return a concise reason to the authorized
requester. Examples include disabled pull strategy, missing/invalid target,
excessive request distance, missing ranged weapon/ammunition, unknown spell,
cooldown, or an unavailable action/current state.

Successful request validation, target choice, movement, range and timing are
unchanged. A pull request may start an approach to a target that is not currently
in casting range or line of sight. Autonomous pull failures remain silent.
This reports request rejection; it does not guarantee that a started pull will
finish if the world changes afterward.

## Read-only status

```text
status role
status build
status pull
```

Example fields:

```text
Role: tank; Range: melee; Spec: fury; SpecSource: dominant_tree
Build: furyprot; Layout: 0/32/19; SuggestedRole: unknown
PullAction: shoot; Ready: no; Reason: ammunition is required; Scope: immediate_cast
```

Role and range use the same grouped/ungrouped core checks as `@tank`, `@heal`,
`@dps`, `@ranged` and `@melee`. If both tank and healer checks match, Role is
`tank+healer`. Spec identifies the dominant talent tree; it does not infer a
hybrid build's intended role.

Build names require an exact talent-layout match to one unambiguous configured
name. Unrecognized or ambiguous layouts return `unknown`. SuggestedRole is
`unknown` because the current build definitions do not provide authoritative
hybrid-role metadata. No talents or strategies are applied by these queries.

`status pull` checks immediate cast readiness against the requester's selected
target. It does not start a pull, change the stored pull target, move the bot or
consume ammunition. A `Ready: no` range/LOS result can coexist with a valid
`pull` request that starts moving into position.

Replies use `Key: value` fields separated by `; `. Reserved punctuation and
control characters in configured names are percent-encoded, and names are
bounded in length. Queries require the same real-player-master/authorized-GM
access as the new preference command and expose no account identifiers.

## Verification and limitations

Focused executable fixtures cover the actual policy persistence methods,
native eligibility in all three cores, fallback behavior, authorization,
invalid input, default and one-time vote isolation, explicit pull failures,
silent autonomous failures, unchanged accepted pulls, status fields and hybrid
ambiguity. The actual save/read statements also passed on temporary tables
cloned from all three dev character schemas, preserving other bot/settings rows.

These are development changes. Native build results are recorded separately
in the task's command-improvements manifest. No production configuration,
database table or server-share binary was changed for this feature. Live
in-game command and logout/relogin checks remain a deployment smoke test.
