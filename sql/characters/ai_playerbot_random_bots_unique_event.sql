-- Required by the single-statement event upsert in RandomPlayerbotMgr.
-- Keep the newest row if an older installation accumulated duplicates.
DELETE stale
FROM `ai_playerbot_random_bots` AS stale
INNER JOIN `ai_playerbot_random_bots` AS newest
    ON newest.`owner` = stale.`owner`
   AND newest.`bot` = stale.`bot`
   AND newest.`event` = stale.`event`
   AND newest.`id` > stale.`id`;

SET @playerbot_event_index_exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'ai_playerbot_random_bots'
      AND index_name = 'owner_bot_event'
);
SET @playerbot_event_index_sql = IF(
    @playerbot_event_index_exists = 0,
    'ALTER TABLE `ai_playerbot_random_bots` ADD UNIQUE KEY `owner_bot_event` (`owner`, `bot`, `event`)',
    'SELECT 1'
);
PREPARE playerbot_event_index_stmt FROM @playerbot_event_index_sql;
EXECUTE playerbot_event_index_stmt;
DEALLOCATE PREPARE playerbot_event_index_stmt;
