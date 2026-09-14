-- Turtle/ManTech destination migration: additive and repeatable.
START TRANSACTION;
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 295,1,1,10 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=295 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=295 AND race=1 AND minl=1 AND maxl=10);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 469,1,30,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=469 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=469 AND race=1 AND minl=30 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 469,3,30,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=469 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=469 AND race=3 AND minl=30 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 469,4,30,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=469 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=469 AND race=4 AND minl=30 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 469,7,30,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=469 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=469 AND race=7 AND minl=30 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 469,10,30,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=469 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=469 AND race=10 AND minl=30 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 1247,3,1,10 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=1247 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=1247 AND race=3 AND minl=1 AND maxl=10);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 1247,7,1,10 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=1247 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=1247 AND race=7 AND minl=1 AND maxl=10);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 1464,3,20,30 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=1464 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=1464 AND race=3 AND minl=20 AND maxl=30);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 1464,7,20,30 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=1464 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=1464 AND race=7 AND minl=20 AND maxl=30);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 2299,1,50,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=2299 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=2299 AND race=1 AND minl=50 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 2299,3,50,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=2299 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=2299 AND race=3 AND minl=50 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 2299,4,50,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=2299 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=2299 AND race=4 AND minl=50 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 2299,7,50,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=2299 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=2299 AND race=7 AND minl=50 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 2299,10,50,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=2299 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=2299 AND race=10 AND minl=50 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 2352,1,20,30 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=2352 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=2352 AND race=1 AND minl=20 AND maxl=30);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 2352,3,20,30 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=2352 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=2352 AND race=3 AND minl=20 AND maxl=30);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 2352,7,20,30 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=2352 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=2352 AND race=7 AND minl=20 AND maxl=30);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 2352,10,20,30 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=2352 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=2352 AND race=10 AND minl=20 AND maxl=30);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 2388,5,20,30 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=2388 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=2388 AND race=5 AND minl=20 AND maxl=30);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 2700,1,30,40 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=2700 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=2700 AND race=1 AND minl=30 AND maxl=40);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 2700,3,30,40 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=2700 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=2700 AND race=3 AND minl=30 AND maxl=40);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 2700,4,30,40 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=2700 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=2700 AND race=4 AND minl=30 AND maxl=40);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 2700,7,30,40 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=2700 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=2700 AND race=7 AND minl=30 AND maxl=40);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 2700,10,30,40 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=2700 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=2700 AND race=10 AND minl=30 AND maxl=40);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 2910,3,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=2910 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=2910 AND race=3 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 2910,7,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=2910 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=2910 AND race=7 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 3934,2,10,25 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=3934 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=3934 AND race=2 AND minl=10 AND maxl=25);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 3934,6,10,25 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=3934 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=3934 AND race=6 AND minl=10 AND maxl=25);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 3934,8,10,25 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=3934 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=3934 AND race=8 AND minl=10 AND maxl=25);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 3934,9,10,25 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=3934 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=3934 AND race=9 AND minl=10 AND maxl=25);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 4048,4,40,50 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=4048 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=4048 AND race=4 AND minl=40 AND maxl=50);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 4500,2,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=4500 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=4500 AND race=2 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 4500,6,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=4500 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=4500 AND race=6 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 4500,8,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=4500 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=4500 AND race=8 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 4500,9,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=4500 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=4500 AND race=9 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 5111,1,10,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=5111 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=5111 AND race=1 AND minl=10 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 5111,3,10,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=5111 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=5111 AND race=3 AND minl=10 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 5111,4,10,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=5111 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=5111 AND race=4 AND minl=10 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 5111,7,10,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=5111 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=5111 AND race=7 AND minl=10 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 5111,10,10,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=5111 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=5111 AND race=10 AND minl=10 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 5688,5,1,10 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=5688 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=5688 AND race=5 AND minl=1 AND maxl=10);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 5814,2,30,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=5814 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=5814 AND race=2 AND minl=30 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 5814,5,30,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=5814 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=5814 AND race=5 AND minl=30 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 5814,6,30,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=5814 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=5814 AND race=6 AND minl=30 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 5814,8,30,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=5814 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=5814 AND race=8 AND minl=30 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 5814,9,30,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=5814 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=5814 AND race=9 AND minl=30 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6272,1,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6272 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6272 AND race=1 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6272,3,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6272 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6272 AND race=3 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6272,7,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6272 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6272 AND race=7 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6272,10,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6272 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6272 AND race=10 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6727,1,15,25 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6727 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6727 AND race=1 AND minl=15 AND maxl=25);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6727,10,15,25 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6727 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6727 AND race=10 AND minl=15 AND maxl=25);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6734,3,10,20 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6734 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6734 AND race=3 AND minl=10 AND maxl=20);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6734,7,10,20 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6734 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6734 AND race=7 AND minl=10 AND maxl=20);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6735,4,10,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6735 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6735 AND race=4 AND minl=10 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6736,4,1,10 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6736 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6736 AND race=4 AND minl=1 AND maxl=10);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6737,4,10,20 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6737 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6737 AND race=4 AND minl=10 AND maxl=20);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6738,4,15,30 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6738 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6738 AND race=4 AND minl=15 AND maxl=30);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6739,5,10,20 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6739 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6739 AND race=5 AND minl=10 AND maxl=20);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6740,1,10,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6740 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6740 AND race=1 AND minl=10 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6740,3,10,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6740 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6740 AND race=3 AND minl=10 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6740,4,10,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6740 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6740 AND race=4 AND minl=10 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6740,7,10,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6740 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6740 AND race=7 AND minl=10 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6740,10,10,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6740 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6740 AND race=10 AND minl=10 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6741,5,10,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6741 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6741 AND race=5 AND minl=10 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6746,6,1,10 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6746 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6746 AND race=6 AND minl=1 AND maxl=10);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6746,6,10,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6746 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6746 AND race=6 AND minl=10 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6790,1,18,30 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6790 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6790 AND race=1 AND minl=18 AND maxl=30);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6790,3,18,30 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6790 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6790 AND race=3 AND minl=18 AND maxl=30);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6790,7,18,30 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6790 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6790 AND race=7 AND minl=18 AND maxl=30);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6790,10,18,30 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6790 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6790 AND race=10 AND minl=18 AND maxl=30);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6791,2,10,25 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6791 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6791 AND race=2 AND minl=10 AND maxl=25);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6791,8,10,25 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6791 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6791 AND race=8 AND minl=10 AND maxl=25);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6791,9,10,25 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6791 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6791 AND race=9 AND minl=10 AND maxl=25);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6807,0,30,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6807 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6807 AND race=0 AND minl=30 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6928,2,1,10 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6928 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6928 AND race=2 AND minl=1 AND maxl=10);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6928,8,1,10 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6928 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6928 AND race=8 AND minl=1 AND maxl=10);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6929,2,10,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6929 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6929 AND race=2 AND minl=10 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6929,5,20,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6929 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6929 AND race=5 AND minl=20 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6929,6,10,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6929 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6929 AND race=6 AND minl=10 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6929,8,10,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6929 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6929 AND race=8 AND minl=10 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6929,9,10,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6929 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6929 AND race=9 AND minl=10 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6930,2,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6930 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6930 AND race=2 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6930,5,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6930 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6930 AND race=5 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6930,6,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6930 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6930 AND race=6 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6930,8,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6930 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6930 AND race=8 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 6930,9,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=6930 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=6930 AND race=9 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 7714,2,10,25 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=7714 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=7714 AND race=2 AND minl=10 AND maxl=25);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 7714,6,10,25 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=7714 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=7714 AND race=6 AND minl=10 AND maxl=25);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 7714,8,10,25 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=7714 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=7714 AND race=8 AND minl=10 AND maxl=25);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 7714,9,10,25 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=7714 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=7714 AND race=9 AND minl=10 AND maxl=25);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 7731,2,15,27 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=7731 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=7731 AND race=2 AND minl=15 AND maxl=27);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 7731,6,15,27 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=7731 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=7731 AND race=6 AND minl=15 AND maxl=27);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 7731,8,15,27 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=7731 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=7731 AND race=8 AND minl=15 AND maxl=27);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 7731,9,15,27 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=7731 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=7731 AND race=9 AND minl=15 AND maxl=27);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 7733,0,40,50 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=7733 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=7733 AND race=0 AND minl=40 AND maxl=50);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 7736,4,40,50 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=7736 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=7736 AND race=4 AND minl=40 AND maxl=50);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 7737,6,40,50 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=7737 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=7737 AND race=6 AND minl=40 AND maxl=50);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 7744,1,40,50 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=7744 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=7744 AND race=1 AND minl=40 AND maxl=50);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 7744,3,40,50 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=7744 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=7744 AND race=3 AND minl=40 AND maxl=50);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 7744,7,40,50 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=7744 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=7744 AND race=7 AND minl=40 AND maxl=50);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 7744,10,40,50 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=7744 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=7744 AND race=10 AND minl=40 AND maxl=50);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 8022,1,45,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=8022 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=8022 AND race=1 AND minl=45 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 8022,3,45,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=8022 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=8022 AND race=3 AND minl=45 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 8022,4,45,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=8022 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=8022 AND race=4 AND minl=45 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 8022,7,45,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=8022 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=8022 AND race=7 AND minl=45 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 8022,10,45,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=8022 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=8022 AND race=10 AND minl=45 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 8587,2,45,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=8587 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=8587 AND race=2 AND minl=45 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 8587,6,45,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=8587 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=8587 AND race=6 AND minl=45 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 8587,8,45,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=8587 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=8587 AND race=8 AND minl=45 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 8587,9,45,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=8587 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=8587 AND race=9 AND minl=45 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 8931,1,10,20 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=8931 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=8931 AND race=1 AND minl=10 AND maxl=20);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 8931,10,10,20 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=8931 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=8931 AND race=10 AND minl=10 AND maxl=20);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9118,2,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9118 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9118 AND race=2 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9118,5,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9118 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9118 AND race=5 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9118,6,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9118 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9118 AND race=6 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9118,8,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9118 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9118 AND race=8 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9118,9,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9118 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9118 AND race=9 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9119,1,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9119 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9119 AND race=1 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9119,3,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9119 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9119 AND race=3 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9119,4,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9119 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9119 AND race=4 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9119,7,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9119 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9119 AND race=7 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9119,10,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9119 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9119 AND race=10 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9356,2,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9356 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9356 AND race=2 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9356,5,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9356 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9356 AND race=5 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9356,6,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9356 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9356 AND race=6 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9356,8,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9356 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9356 AND race=8 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9356,9,35,45 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9356 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9356 AND race=9 AND minl=35 AND maxl=45);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9465,1,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9465 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9465 AND race=1 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9465,3,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9465 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9465 AND race=3 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9465,4,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9465 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9465 AND race=4 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9465,7,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9465 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9465 AND race=7 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9465,10,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9465 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9465 AND race=10 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9501,2,30,40 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9501 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9501 AND race=2 AND minl=30 AND maxl=40);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9501,5,30,40 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9501 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9501 AND race=5 AND minl=30 AND maxl=40);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9501,6,30,40 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9501 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9501 AND race=6 AND minl=30 AND maxl=40);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9501,8,30,40 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9501 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9501 AND race=8 AND minl=30 AND maxl=40);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9501,9,30,40 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9501 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9501 AND race=9 AND minl=30 AND maxl=40);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9996,2,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9996 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9996 AND race=2 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9996,5,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9996 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9996 AND race=5 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9996,6,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9996 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9996 AND race=6 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9996,8,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9996 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9996 AND race=8 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 9996,9,48,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=9996 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=9996 AND race=9 AND minl=48 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 11056,1,51,58 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=11056 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=11056 AND race=1 AND minl=51 AND maxl=58);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 11056,3,51,58 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=11056 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=11056 AND race=3 AND minl=51 AND maxl=58);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 11056,4,51,58 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=11056 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=11056 AND race=4 AND minl=51 AND maxl=58);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 11056,7,51,58 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=11056 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=11056 AND race=7 AND minl=51 AND maxl=58);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 11056,10,51,58 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=11056 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=11056 AND race=10 AND minl=51 AND maxl=58);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 11103,4,30,40 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=11103 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=11103 AND race=4 AND minl=30 AND maxl=40);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 11106,2,30,40 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=11106 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=11106 AND race=2 AND minl=30 AND maxl=40);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 11106,6,30,40 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=11106 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=11106 AND race=6 AND minl=30 AND maxl=40);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 11106,8,30,40 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=11106 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=11106 AND race=8 AND minl=30 AND maxl=40);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 11106,9,30,40 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=11106 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=11106 AND race=9 AND minl=30 AND maxl=40);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 11116,2,25,35 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=11116 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=11116 AND race=2 AND minl=25 AND maxl=35);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 11116,6,25,35 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=11116 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=11116 AND race=6 AND minl=25 AND maxl=35);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 11116,8,25,35 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=11116 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=11116 AND race=8 AND minl=25 AND maxl=35);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 11116,9,25,35 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=11116 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=11116 AND race=9 AND minl=25 AND maxl=35);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 11118,0,53,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=11118 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=11118 AND race=0 AND minl=53 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 11548,1,45,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=11548 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=11548 AND race=1 AND minl=45 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 11548,4,45,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=11548 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=11548 AND race=4 AND minl=45 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 11548,10,45,55 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=11548 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=11548 AND race=10 AND minl=45 AND maxl=55);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 12196,2,18,30 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=12196 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=12196 AND race=2 AND minl=18 AND maxl=30);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 12196,8,18,30 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=12196 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=12196 AND race=8 AND minl=18 AND maxl=30);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 12196,9,18,30 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=12196 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=12196 AND race=9 AND minl=18 AND maxl=30);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 12719,2,18,30 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=12719 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=12719 AND race=2 AND minl=18 AND maxl=30);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 12719,8,18,30 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=12719 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=12719 AND race=8 AND minl=18 AND maxl=30);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 12719,9,18,30 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=12719 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=12719 AND race=9 AND minl=18 AND maxl=30);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 13177,2,50,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=13177 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=13177 AND race=2 AND minl=50 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 13177,5,50,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=13177 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=13177 AND race=5 AND minl=50 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 13177,6,50,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=13177 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=13177 AND race=6 AND minl=50 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 13177,8,50,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=13177 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=13177 AND race=8 AND minl=50 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 13177,9,50,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=13177 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=13177 AND race=9 AND minl=50 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 14624,0,45,50 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=14624 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=14624 AND race=0 AND minl=45 AND maxl=50);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 14731,2,40,50 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=14731 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=14731 AND race=2 AND minl=40 AND maxl=50);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 14731,5,40,50 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=14731 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=14731 AND race=5 AND minl=40 AND maxl=50);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 14731,6,40,50 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=14731 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=14731 AND race=6 AND minl=40 AND maxl=50);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 14731,8,40,50 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=14731 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=14731 AND race=8 AND minl=40 AND maxl=50);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 14731,9,40,50 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=14731 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=14731 AND race=9 AND minl=40 AND maxl=50);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 15174,0,55,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=15174 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=15174 AND race=0 AND minl=55 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 16256,0,53,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=16256 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=16256 AND race=0 AND minl=53 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 16458,4,15,27 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=16458 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=16458 AND race=4 AND minl=15 AND maxl=27);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 16602,2,58,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=16602 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=16602 AND race=2 AND minl=58 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 16602,5,58,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=16602 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=16602 AND race=5 AND minl=58 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 16602,6,58,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=16602 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=16602 AND race=6 AND minl=58 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 16602,8,58,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=16602 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=16602 AND race=8 AND minl=58 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 16602,9,58,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=16602 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=16602 AND race=9 AND minl=58 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 16739,1,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=16739 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=16739 AND race=1 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 16739,3,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=16739 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=16739 AND race=3 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 16739,4,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=16739 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=16739 AND race=4 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 16739,7,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=16739 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=16739 AND race=7 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 16739,10,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=16739 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=16739 AND race=10 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 16826,1,58,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=16826 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=16826 AND race=1 AND minl=58 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 16826,3,58,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=16826 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=16826 AND race=3 AND minl=58 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 16826,4,58,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=16826 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=16826 AND race=4 AND minl=58 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 16826,7,58,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=16826 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=16826 AND race=7 AND minl=58 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 16826,10,58,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=16826 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=16826 AND race=10 AND minl=58 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 17079,2,55,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=17079 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=17079 AND race=2 AND minl=55 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 17079,5,55,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=17079 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=17079 AND race=5 AND minl=55 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 17079,6,55,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=17079 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=17079 AND race=6 AND minl=55 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 17079,8,55,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=17079 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=17079 AND race=8 AND minl=55 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 17079,9,55,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=17079 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=17079 AND race=9 AND minl=55 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 17080,1,55,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=17080 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=17080 AND race=1 AND minl=55 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 17080,3,55,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=17080 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=17080 AND race=3 AND minl=55 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 17080,4,55,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=17080 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=17080 AND race=4 AND minl=55 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 17080,7,55,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=17080 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=17080 AND race=7 AND minl=55 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 17080,10,55,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=17080 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=17080 AND race=10 AND minl=55 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 17630,2,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=17630 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=17630 AND race=2 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 17630,5,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=17630 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=17630 AND race=5 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 17630,6,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=17630 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=17630 AND race=6 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 17630,8,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=17630 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=17630 AND race=8 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 17630,9,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=17630 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=17630 AND race=9 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18245,2,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18245 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18245 AND race=2 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18245,5,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18245 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18245 AND race=5 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18245,6,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18245 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18245 AND race=6 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18245,8,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18245 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18245 AND race=8 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18245,9,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18245 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18245 AND race=9 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18251,1,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18251 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18251 AND race=1 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18251,3,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18251 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18251 AND race=3 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18251,4,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18251 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18251 AND race=4 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18251,7,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18251 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18251 AND race=7 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18251,10,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18251 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18251 AND race=10 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18905,2,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18905 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18905 AND race=2 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18905,5,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18905 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18905 AND race=5 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18905,6,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18905 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18905 AND race=6 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18905,8,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18905 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18905 AND race=8 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18905,9,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18905 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18905 AND race=9 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18906,1,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18906 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18906 AND race=1 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18906,3,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18906 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18906 AND race=3 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18906,4,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18906 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18906 AND race=4 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18906,7,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18906 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18906 AND race=7 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18906,10,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18906 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18906 AND race=10 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 18907,0,60,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=18907 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=18907 AND race=0 AND minl=60 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 19229,1,58,59 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=19229 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=19229 AND race=1 AND minl=58 AND maxl=59);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 19229,3,58,59 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=19229 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=19229 AND race=3 AND minl=58 AND maxl=59);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 19229,4,58,59 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=19229 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=19229 AND race=4 AND minl=58 AND maxl=59);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 19229,7,58,59 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=19229 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=19229 AND race=7 AND minl=58 AND maxl=59);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 19229,10,58,59 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=19229 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=19229 AND race=10 AND minl=58 AND maxl=59);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 19253,2,58,59 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=19253 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=19253 AND race=2 AND minl=58 AND maxl=59);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 19253,5,58,59 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=19253 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=19253 AND race=5 AND minl=58 AND maxl=59);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 19253,6,58,59 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=19253 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=19253 AND race=6 AND minl=58 AND maxl=59);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 19253,8,58,59 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=19253 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=19253 AND race=8 AND minl=58 AND maxl=59);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 19253,9,58,59 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=19253 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=19253 AND race=9 AND minl=58 AND maxl=59);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 61724,9,1,9 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=61724 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=61724 AND race=9 AND minl=1 AND maxl=9);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 61831,10,10,60 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=61831 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=61831 AND race=10 AND minl=10 AND maxl=60);
INSERT INTO ai_playerbot_rpg_races (entry,race,minl,maxl)
SELECT 80227,10,1,9 FROM DUAL
WHERE EXISTS (SELECT 1 FROM creature c JOIN creature_template t ON t.entry=c.id WHERE c.id=80227 AND c.map IN (0,1) AND (t.npc_flags & 128))
AND NOT EXISTS (SELECT 1 FROM ai_playerbot_rpg_races WHERE entry=80227 AND race=10 AND minl=1 AND maxl=9);
COMMIT;
