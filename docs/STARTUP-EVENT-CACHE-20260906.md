# Startup event-cache diagnostics

The last `Enhancing RPG teleport cache` message did not identify the entire
subsequent startup delay. After preparing destinations, RandomPlayerbotMgr loads
saved events for every bot and synchronizes global event timers. Those operations
previously had no progress messages. Startup now logs destination preparation by
phase and saved-event loading separately, including elapsed time.

The production incident also exposed a missing required database migration:
`sql/characters/ai_playerbot_random_bots_unique_event.sql`. The existing event
writer uses `ON DUPLICATE KEY UPDATE` and requires uniqueness of
`(owner, bot, event)`. Without the unique key it inserts duplicate event rows.
The migration predates these startup diagnostics and the combat enhancement work.

Before deployment, verify a non-prefix unique key on exactly those three columns
in every active character database. On large duplicate tables, the migration's
self-join can be expensive. A maintenance alternative is to stop the realm,
retain the original table, and build a replacement selecting MAX(id) per non-NULL
owner/bot/event group, preserving NULL-event rows and every retained column. Verify
counts, original checksums, and the unique index before an atomic table rename.
Do not truncate the event table or reset player characters to address this issue.

The destination timing messages do not change destination selection, bot limits,
travel settings, or encounter behavior.
