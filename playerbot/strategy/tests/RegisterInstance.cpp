#ifdef MANTECH_RAID_LAB
#include "World/RaidLab.h"
#include "RaidLabRoutes.h"
#include "RaidLabPacks.h"
#include "Maps/SpawnGroupDefines.h"
#endif
#include "playerbot/playerbot.h"
#include "TestRegistry.h"
#include "playerbot/TravelMgr.h"
#include "playerbot/TravelNode.h"

#include <algorithm>
#include <functional>
#include <sstream>

#include "Server/DBCStores.h"

using namespace ai;

namespace
{
    using ScenarioParams = std::map<std::string, std::string>;

    bool ResolveInstanceEntry(const MapEntry* mapEntry, std::string& mapName, GuidPosition& entry)
    {


        TravelNode* best = nullptr;
        for (auto& node : sTravelNodeMap.getNodes())
        {
            if (node->getMapId() != mapEntry->MapID)
                continue;

            std::string nodeName = node->getName();
            std::transform(nodeName.begin(), nodeName.end(), nodeName.begin(), ::tolower);
            if (nodeName.find("entrance") != std::string::npos)
            {
                best = node;
                break;
            }

            if (!best && node->isPortal())
                best = node;
        }

        if (!best)
        {
            static std::set<uint32> loggedMaps;
            if (loggedMaps.insert(mapEntry->MapID).second)
                sLog.outError("[TESTGEN] no travel node on instance map %u (%s) - scenario tests skipped for it",
                    mapEntry->MapID, mapEntry->name[0]);
            return false;
        }


        mapName = mapEntry->name[0];
        mapName.erase(std::remove_if(mapName.begin(), mapName.end(), ::isspace), mapName.end());
        mapName += "_inside";
        TestRegistry::RegisterNamedLocation(mapName, GuidPosition(ObjectGuid(), *best->getPosition()));
        return TestRegistry::ParseLocation(mapName, entry) && entry.getMapId() == mapEntry->MapID;
    }
}

std::string TestRegistry::ApplyScenarioParams(const std::string& line, const std::map<std::string, std::string>& params)
{
    std::string expanded = line;
    for (const auto& pair : params)
    {
        const std::string token = "$(" + pair.first + ")";
        size_t pos = 0;
        while ((pos = expanded.find(token, pos)) != std::string::npos)
        {
            expanded.replace(pos, token.length(), pair.second);
            pos += pair.second.length();
        }
    }

    return expanded;
}

std::vector<std::string> TestRegistry::ApplyScenarioParams(const std::vector<std::string>& script,
    const std::map<std::string, std::string>& params)
{
    std::vector<std::string> expanded;
    expanded.reserve(script.size());
    for (const std::string& line : script)
        expanded.push_back(ApplyScenarioParams(line, params));

    return expanded;
}

namespace
{
    // File-local duplicate of the (private) TestRegistry::ApplyScenarioParams line expansion;
    // kept here so the header stays untouched.
    std::string ExpandScenarioLine(const std::string& line, const ScenarioParams& params)
    {
        std::string expanded = line;
        for (const auto& pair : params)
        {
            const std::string token = "$(" + pair.first + ")";
            size_t pos = 0;
            while ((pos = expanded.find(token, pos)) != std::string::npos)
            {
                expanded.replace(pos, token.length(), pair.second);
                pos += token.length();
            }
        }

        return expanded;
    }

    // Encounter-teleport approach point (operator request, 2026-09-30): instead of dropping the raid
    // on top of the boss, place it 1.5x the boss's aggro radius away, on the travel-node path from
    // the boss toward an instance exit (i.e. where a group arriving through the instance would stand).
    // Aggro radius mirrors the core's documented model (Unit::GetAttackDistance): 18 yd at equal
    // level, -1 yd per player level above the mob, floored at 5 yd, scaled by the aggro rate config.
    // Returns the point as a "mapId;x;y;z;0" string; falls back to the boss position itself when no
    // route/exit can be resolved (with a [TESTGEN] note).
    std::string ComputeBossApproachCoords(const MapEntry* mapEntry, const WorldPosition& bossPos,
                                          uint32 bossLevel, uint32 botLevel)
    {
        float aggroRate = sWorld.getConfig(CONFIG_FLOAT_RATE_CREATURE_AGGRO);
        if (aggroRate <= 0.0f)
            aggroRate = 1.0f;

        const float aggroRadius = std::max(5.0f, 18.0f - float(int32(botLevel) - int32(bossLevel))) * aggroRate;
        const float approachDist = 1.5f * aggroRadius;

        auto formatCoords = [](const WorldPosition& pos)
        {
            std::ostringstream out;
            out << pos.getMapId() << ";" << pos.getX() << ";" << pos.getY() << ";" << pos.getZ() << ";0";
            return out.str();
        };

        // Boss node: nearest travel node on the instance map. Exit node: name contains "exit".
        TravelNode* bossNode = nullptr;
        TravelNode* exitNode = nullptr;
        float bossNodeDist = FLT_MAX;

        for (TravelNode* node : sTravelNodeMap.getNodes())
        {
            if (!node || node->getMapId() != mapEntry->MapID)
                continue;

            const float dist = node->getDistance(bossPos);
            if (dist < bossNodeDist)
            {
                bossNodeDist = dist;
                bossNode = node;
            }

            std::string nodeName = node->getName();
            std::transform(nodeName.begin(), nodeName.end(), nodeName.begin(), ::tolower);
            if (nodeName.find("exit") != std::string::npos && (!exitNode || dist < exitNode->getDistance(bossPos)))
                exitNode = node;
        }

        if (!exitNode)
        {
            static std::set<uint32> loggedMaps;
            if (loggedMaps.insert(mapEntry->MapID).second)
                sLog.outError("[TESTGEN] no instance-exit travel node on map %u (%s) - encounter approaches via entrance node",
                    mapEntry->MapID, mapEntry->name[0]);

            std::string entranceName = mapEntry->name[0];
            entranceName.erase(std::remove_if(entranceName.begin(), entranceName.end(), ::isspace), entranceName.end());
            entranceName += "_inside";
            GuidPosition entry;
            if (TestRegistry::ParseLocation(entranceName, entry))
            {
                for (TravelNode* node : sTravelNodeMap.getNodes())
                {
                    if (node && node->getMapId() == mapEntry->MapID && node->getDistance(entry) < 5.0f)
                        exitNode = node;
                }
            }
        }

        if (!exitNode || !bossNode)
            return formatCoords(bossPos);

        // Polyline: boss position -> (route node positions) -> exit node position.
        std::vector<WorldPosition> line;
        line.push_back(bossPos);

        TravelNodeRoute route = sTravelNodeMap.getRoute(bossNode, exitNode);
        if (!route.isEmpty())
        {
            bool first = true;
            for (TravelNode* node : route.getNodes())
            {
                if (first && node == bossNode)
                    continue;
                line.push_back(*node->getPosition());
                first = false;
            }
        }

        line.push_back(*exitNode->getPosition());

        // Walk the polyline from the boss and interpolate where the approach distance is crossed.
        float travelled = 0.0f;
        for (size_t i = 0; i + 1 < line.size(); ++i)
        {
            const WorldPosition& from = line[i];
            const WorldPosition& to = line[i + 1];
            const float segLen = from.distance(to);
            if (segLen <= 0.0f)
                continue;

            if (travelled + segLen >= approachDist)
            {
                const float t = (approachDist - travelled) / segLen;
                const WorldPosition approachPos(bossPos.getMapId(),
                    from.getX() + (to.getX() - from.getX()) * t,
                    from.getY() + (to.getY() - from.getY()) * t,
                    from.getZ() + (to.getZ() - from.getZ()) * t,
                    from.getO());
                return formatCoords(approachPos);
            }
            travelled += segLen;
        }

        // Route shorter than the approach distance: use its midpoint (still on the real path).
        static std::set<uint32> loggedShort;
        if (loggedShort.insert(mapEntry->MapID).second)
            sLog.outError("[TESTGEN] approach distance %.1f exceeds route on map %u (%s) - using route midpoint",
                approachDist, mapEntry->MapID, mapEntry->name[0]);

        return formatCoords(line[line.size() / 2]);
    }

    // Difficulty variants (operator request, 2026-09-30): every instance scenario registers three
    // times, differing only in the bots' level:
    //   MIN   = the dungeon's levelMin            -> test name gets a "_min" suffix
    //   BOOST = levelMin + 10 (the old default)   -> keeps the untagged name, so existing test
    //                                              names and result history stay valid
    //   MAX   = the tree's player level cap       -> test name gets a "_max" suffix
    //           (DEFAULT_MAX_LEVEL is 60/70/80 across classic/tbc/wotlk trees)
    // MIN is the only variant that fights the content at true level (the other two outlevel it);
    // expect the trash templates' pass monitors (dead mobs / party xp) to be the hard ones there.
    void RegisterInstanceScenario(const char* prefix, const std::string& bossName,
                                  const std::vector<std::string>& tmpl, const ScenarioParams& params, uint32 levelMin,
                                  const std::function<void(ScenarioParams&, uint32 botLevel)>& adjustPerVariant = {})
    {
        struct Variant { const char* suffix; uint32 level; };
        std::vector<Variant> variants = {
            { "_min", levelMin },
            { "",     levelMin + 10 },
            { "_max", uint32(DEFAULT_MAX_LEVEL) },
        };
#ifdef MANGOSBOT_TWO
        if (70 <= DEFAULT_MAX_LEVEL)
            variants.push_back({ "_70", 70 });
#endif

        for (const Variant& variant : variants)
        {
            ScenarioParams leveled = params;
            leveled["level"] = std::to_string(variant.level);
            if (adjustPerVariant)
                adjustPerVariant(leveled, variant.level);

            std::vector<std::string> expanded;
            expanded.reserve(tmpl.size());
            for (const std::string& line : tmpl)
                expanded.push_back(ExpandScenarioLine(line, leveled));

            TestRegistry::RegisterTest(std::string(prefix) + bossName + variant.suffix, expanded);
        }
    }
}

void TestRegistry::GenerateBossWalkTest()
{
    // maxDistance 0: the generator uses an EMPTY PlayerTravelInfo whose center is the map-0 origin
    // (0,0,0). The default maxDistance of 10000 yd then silently dropped every destination whose
    // portal was farther than that from the origin - Zul'Gurub (map 309) bosses were all >10000 and
    // generated no tests at all (BL-45). The generator teleports bots to the instance, so travel
    // distance is irrelevant here; only the FLT_MAX unpathable-map check should apply.
    DestinationList bossDestinations = sTravelMgr.GetDestinations(PlayerTravelInfo(), (uint32)TravelDestinationPurpose::Boss, {}, false, 0);

    std::vector<std::string> instanceGroupTemplate = {
        "# instance progression with large group and dead-mob observation",
        "require bot is level=$(level)",
        "monitor dead mobs > $(dead_mobs_min) => pass \"Observed dead mobs in instance\"",
        "monitor party xp > $(party_xp_min) => pass \"Party gained xp clearing trash\"",
        "monitor time > $(timeout_s) => fail \"Timeout while traversing instance after <time elapsed> (mobs <mobs killed>, traveled <distance traveled> / wanted <distance wanted>)\"",
        "mgroup size=$(group_size) gear=best",
        "gm visible on",
        "gm off",
        "wait group $(group_size) 180",
        "teleport $(instance_entry)",
        // BL-42 follow-up: a lost mgroup join used to surface as the group-size monitor's
        // misleading "Group dissolved" (party formed one short but otherwise healthy).
        // Abort honestly at delivery time instead: "group never formed (size 4 < expected 5)".
        "teleport group expect=$(group_size)",
        "wait 10",
        "$(start_command)",
        "set destination $(boss_destination)",
        "wait 60",
        "monitor not on map $(instance_entry) => abort \"Bot left instance map\"",
        "monitor group size < $(group_size) => abort \"Group dissolved\"",
        "observe"};

    for (auto& destination : bossDestinations)
    {
        for (auto& point : destination->GetPoints())
        {
            if (!point->getMapEntry())
                continue;

            const MapEntry* mapEntry = point->getMapEntry();

            if (!mapEntry->IsDungeon())
                continue;

            const InstanceTemplate* instanceTemplate = point->getInstanceTemplate();
            if (!instanceTemplate)
                continue;

            CreatureInfo const* bossInfo = static_cast<BossTravelDestination*>(destination)->GetCreatureInfo();
            if (!bossInfo)
                continue;

            GuidPosition entry;
            std::string mapName = mapEntry->name[0];

            if (!ParseLocation(mapName, entry))
            {
                mapName.erase(remove_if(mapName.begin(), mapName.end(), isspace), mapName.end());
            }

            if (!ParseLocation(mapName, entry))
            {
                if (mapName.find(" ") != std::string::npos)
                    mapName = mapName.substr(0, mapName.find(" "));
            }

            if (!ResolveInstanceEntry(mapEntry, mapName, entry))
                continue;

            std::string startCommand = ".bot p @tank co + mark rti";
            std::string maxPlayers = "5";

            if (mapEntry->IsRaid())
            {
#if defined(MANGOSBOT_ZERO) || defined(MANGOSBOT_ONE)
                maxPlayers = std::to_string(instanceTemplate->maxPlayers);
#else
                if (MapDifficultyEntry const* mapDiff = GetMapDifficultyData(mapEntry->MapID, REGULAR_DIFFICULTY))
                    maxPlayers = std::to_string(mapDiff->maxPlayers);
                else
                    maxPlayers = "25";
#endif
                startCommand = ".bot r @tank co + mark rti";
            }

            std::string bossName = mapEntry->name[0] + std::string("_") + bossInfo->Name;
            std::replace(bossName.begin(), bossName.end(), ' ', '_');
            std::replace(bossName.begin(), bossName.end(), '\'', '_');
            std::transform(bossName.begin(), bossName.end(), bossName.begin(), ::tolower);

            RegisterNamedLocation(bossName, GuidPosition(ObjectGuid(), *point));

            RegisterInstanceScenario("scenario_trash_", bossName, instanceGroupTemplate, ScenarioParams{
                {"timeout_s",        "1200"                                         },
                {"start_command",    startCommand                                   },
                {"group_size",       maxPlayers                                     },
                {"dead_mobs_min",    "5"                                            },
                {"party_xp_min",     "5000"                                         },
                {"instance_entry",   mapName                                        },
                {"boss_destination", bossName                                       }
            }, instanceTemplate->levelMin);
        }
    }
}

void TestRegistry::GenerateBossEncounterTest()
{
#ifdef MANTECH_RAID_LAB
    if (RaidLab::Enabled())
    {
        // Explicit native group fixtures complement entrance corridors. Each
        // runtime test records only the actual random entries present; friendly
        // groups and boss/event actors are rejected by the staging command.
        const auto groups=sObjectMgr.GetSpawnGroupContainer();
        if(groups)for(const auto& pair:groups->spawnGroupMap) {
            const auto& group=pair.second;
            if(group.Type!=SPAWN_GROUP_CREATURE || group.DbGuids.empty() || group.DbGuids.size()>64)continue;
            const CreatureData* first=sObjectMgr.GetCreatureData(group.DbGuids.front().DbGuid);
            if(!first || !RaidLab::AllowedMap(first->mapid))continue;
            bool sameMap=true;
            for(const auto& spawn:group.DbGuids) {
                const CreatureData* member=sObjectMgr.GetCreatureData(spawn.DbGuid);
                if(!member || member->mapid!=first->mapid){sameMap=false;break;}
            }
            if(!sameMap)continue;
            const uint32 map=first->mapid;const std::string id=std::to_string(group.Id);
            const std::string size=map==309 || map==509?"20":"40";
            const MapEntry* native=sMapStore.LookupEntry(map);GuidPosition portal;std::string mapName;
            if(!native || !ResolveInstanceEntry(native,mapName,portal))continue;
            std::ostringstream point;point<<map<<';'<<first->posX<<';'<<first->posY<<';'<<first->posZ<<";0";
            RegisterTest("raidlab_"+std::to_string(map)+"_pack_"+id+"_leader",{
                "require bot is level=60","mgroup size="+size+" gear=best","wait group "+size+" 180",
                "gm on","teleport "+mapName,"wait 5","teleport "+point.str(),"wait 10",
                "raidlab pack "+id+" stage","wait 5","raidlab leader","teleport group expect="+size,
                "wait 5","raidlab leader settled","gm off","raidlab pack "+id+" fight"
            });
        }
        for(const auto& pack:RaidLabLinkedPacks()) {
            const CreatureData* first=sObjectMgr.GetCreatureData(pack.first);
            if(!first || !RaidLab::AllowedMap(first->mapid))continue;
            const uint32 map=first->mapid;const std::string id=std::to_string(pack.first);
            const std::string size=map==309 || map==509?"20":"40";
            const MapEntry* native=sMapStore.LookupEntry(map);GuidPosition portal;std::string mapName;
            if(!native || !ResolveInstanceEntry(native,mapName,portal))continue;
            std::ostringstream point;point<<map<<';'<<first->posX<<';'<<first->posY<<';'<<first->posZ<<";0";
            RegisterTest("raidlab_"+std::to_string(map)+"_linked_"+id+"_leader",{
                "require bot is level=60","mgroup size="+size+" gear=best","wait group "+size+" 180",
                "gm on","teleport "+mapName,"wait 5","teleport "+point.str(),"wait 10",
                "raidlab pack "+id+" stage-linked","wait 5","raidlab leader","teleport group expect="+size,
                "wait 5","raidlab leader settled","gm off","raidlab pack "+id+" fight-linked"
            });
        }
        for(const auto& corridor:RaidLabCorridorRoutes) {
            const uint32 map=corridor.map;const std::string size=std::to_string(corridor.size);
            const MapEntry* native=sMapStore.LookupEntry(map);GuidPosition portal;std::string mapName;
            if(!native || !ResolveInstanceEntry(native,mapName,portal))continue;
            const bool suppression=map==469;
            RegisterTest("raidlab_"+std::to_string(map)+"_"+std::to_string(corridor.boss)+"_leader_progression",{
                "require bot is level=60","mgroup size="+size+" gear=best","wait group "+size+" 180",
                "gm on","teleport "+mapName,"wait 5",
                suppression?"teleport 469;-7578;-895;428.25;0":"wait 1",
                "wait 5",suppression?"raidlab landing 12465":"wait 1",
                "wait 5","raidlab leader","teleport group expect="+size,"wait 5","raidlab leader settled","gm off",
                std::string("raidlab corridor ")+corridor.name,
                "monitor raidlab boss dead => pass \"Native corridor and boss outcome observed; mechanics acceptance separate\"",
                "monitor time > 900 => fail \"Corridor final boss combat timeout\"",
                "monitor party wiped => fail \"Corridor raid wiped\"",
                "monitor group size < "+size+" => abort \"Corridor raid lost members\"",
                "monitor not on map "+mapName+" => abort \"Leader left corridor instance\"","observe"
            });
        }
        struct NativeEventFixture { uint32 map,boss,size;const char* position;const char* activation; };
        const NativeEventFixture events[] = {
            // Even GM scouts trigger the native birth trap. Start60yd west
            // of GO181356; landing admission then chooses a verified floor/path.
            {533,15989,40,"533;3462.57;-5236.76;137.63;0","trap 181356"},
            {533,16060,40,"533;2697;-3378;267.504;3.14159","gothik 16060"},
            {533,15990,40,"533;3716.38;-5106.78;141.29;0","area 4112"},
            {533,15928,40,"533;3508.85;-2994.08;312.18;0","phase 15930"},
            {531,15727,40,"531;-8606.67;2000.57;103.056;0","phase 15589"},
            {309,11382,20,"309;-12223;-1936;130.31;0","phase 11391"},
            // The previous point west of the gong failed native floor
            // admission. Try the room side, toward aArlokkWallShieldPos;
            // all party floor checks remain mandatory before activation.
            {309,14515,20,"309;-11565.199;-1627.874;41.277;3.14159","go 180526"},
            {531,15517,40,"531;-9143.58;2103.85;-64.7893;3.14159","approach 15957"},
            {469,11583,40,"469;-7586.27;-1261.92;482.03;3.14159","gossip 10162"},
            {469,13020,40,"469;-7529.10;-1007.19;408.565;0","vael 3626"},
            {469,14020,40,"469;-7512.98;-1094.69;476.554;0","go-existing 179148"},
            {469,12435,40,"469;-7602.11;-1094.50;408.490;0","razorgore 12557"},
            {409,11502,40,"409;846.933;-812.875;-229.601;0","gossip 12018"},
            {309,15114,20,"309;-11683.4;-1782.9;12.59;0","item 19974"},
            {309,15082,20,"309;-11884.5;-1888;63.504;0","madness 19931"},
            {309,15083,20,"309;-11884.5;-1888;63.504;0","madness 19931"},
            {309,15084,20,"309;-11884.5;-1888;63.504;0","madness 19931"},
            {309,15085,20,"309;-11884.5;-1888;63.504;0","madness 19931"}
        };
        for (const auto& event:events)
        {
            const MapEntry* map=sMapStore.LookupEntry(event.map);GuidPosition entrance;std::string name;
            if(!map || !ResolveInstanceEntry(map,name,entrance)) continue;
            const std::vector<std::string> preparations=event.map==469 || event.boss==15989
                ? std::vector<std::string>{"","_prepared"}:event.boss==15114 || (event.boss>=15082 && event.boss<=15085)
                ? std::vector<std::string>{"_prepared"}:std::vector<std::string>{""};
            for(const auto& preparation:preparations)
            RegisterTest("raidlab_"+std::to_string(event.map)+"_"+std::to_string(event.boss)+
                (event.boss==11502?"_leader_seeded_event":"_leader_event")+preparation,{
                "require bot is level=60","mgroup size="+std::to_string(event.size)+" gear=best",
                "wait group "+std::to_string(event.size)+" 180","gm on","teleport "+name,"wait 5",
                // Freeze the synthetic human before entering the event room:
                // autonomous RPG actions must not activate its GO during setup.
                "raidlab leader",
                "teleport "+std::string(event.position),"wait 5",
                event.boss==11502?"raidlab seed ragnaros":
                    (event.map==309 && event.boss>=15082 && event.boss<=15085)?
                    "raidlab staging "+std::to_string(event.boss)+" madness-room":"wait 1",
                event.boss==15989?"raidlab landing 15989":event.boss==15928?"raidlab landing 15930":event.boss==15727?"raidlab landing 15589":event.boss==11382?"raidlab landing 11391":"wait 1","wait 5",
                "raidlab leader","teleport group expect="+std::to_string(event.size),"wait 5","raidlab leader settled","gm off",
                !preparation.empty() && event.map==469?"raidlab provision bwl":
                !preparation.empty() && event.boss==15989?"raidlab provision sapphiron":"wait 1",
                "raidlab event "+std::to_string(event.boss)+" "+event.activation,
                "monitor raidlab boss dead => pass \"Observed native event boss death; mechanic coverage separate\"",
                "monitor raidlab no engagement => fail \"Event boss did not engage\"",
                "monitor time > 900 => fail \"Event encounter timeout\"",
                "monitor party wiped => fail \"Event raid wiped\"",
                "monitor not on map "+name+" => abort \"Leader left map\"",
                "monitor group size < "+std::to_string(event.size)+" => abort \"Group lost members\"","observe"
            });
        }
        const MapEntry* mc=sMapStore.LookupEntry(409);GuidPosition mcEntry;std::string mcName;
        if(mc && ResolveInstanceEntry(mc,mcName,mcEntry))
            RegisterTest("raidlab_409_12018_leader_seeded",{
                "require bot is level=60","mgroup size=40 gear=best","wait group 40 180",
                "gm on","teleport "+mcName,"wait 5",
                "teleport 409;713;-1176;-118.6403;0","wait 5","raidlab seed majordomo","wait 5",
                "raidlab landing 12018","wait 5","raidlab leader","teleport group expect=40","wait 5","raidlab leader settled","gm off",
                "raidlab 12018 leader",
                "monitor raidlab encounter complete => pass \"Native Majordomo surrender observed; prerequisite and mechanics coverage separate\"",
                "monitor raidlab no engagement => fail \"Majordomo did not engage\"",
                "monitor time > 900 => fail \"Majordomo encounter timeout\"",
                "monitor party wiped => fail \"Majordomo raid wiped\"",
                "monitor not on map "+mcName+" => abort \"Leader left map\"",
                "monitor group size < 40 => abort \"Group lost members\"","observe"
            });
        const MapEntry* aq20=sMapStore.LookupEntry(509);GuidPosition aqEntry;std::string aqName;
        if(aq20 && ResolveInstanceEntry(aq20,aqName,aqEntry))
            RegisterTest("raidlab_509_15341_leader_progression",{
                "require bot is level=60","mgroup size=20 gear=best","wait group 20 180",
                "gm on","teleport "+aqName,"wait 5",
                "teleport 509;-8799.76;1610.12;21.7588;0","wait 5",
                "raidlab landing 15348","wait 5","raidlab leader","teleport group expect=20","wait 5","raidlab leader settled","gm off",
                "raidlab progression rajaxx",
                "monitor raidlab boss dead => pass \"Native Kurinnaxx-Andorov-Rajaxx progression observed; mechanics acceptance separate\"",
                "monitor time > 600 => fail \"Rajaxx final combat timeout\"",
                "monitor party wiped => fail \"Progression raid wiped\"",
                "monitor not on map "+aqName+" => abort \"Leader left native progression instance\"",
                "monitor group size < 20 => abort \"Progression group lost members\"","observe"
            });
    }
#endif
    // maxDistance 0: the generator uses an EMPTY PlayerTravelInfo whose center is the map-0 origin
    // (0,0,0). The default maxDistance of 10000 yd then silently dropped every destination whose
    // portal was farther than that from the origin - Zul'Gurub (map 309) bosses were all >10000 and
    // generated no tests at all (BL-45). The generator teleports bots to the instance, so travel
    // distance is irrelevant here; only the FLT_MAX unpathable-map check should apply.
    DestinationList bossDestinations = sTravelMgr.GetDestinations(PlayerTravelInfo(), (uint32)TravelDestinationPurpose::Boss, {}, false, 0);

    std::vector<std::string> bossEncounterTemplate = {
        "# Boss encounter test - teleport near boss, clear trash, fight boss",
        "require bot is level=$(level)",
        "monitor mob $(boss_entry) is dead => pass \"Boss $(boss_name) killed\"",
        "monitor time > $(timeout_s) => fail \"Timeout: boss not killed after <time elapsed>\"",
        "monitor party wiped => fail \"Party wiped on $(boss_name)\"",
        "monitor bot dead => abort \"Bot died: released to graveyard and timed out in revive\"",
        "monitor not on map $(instance_entry) => abort \"Bot left instance map\"",
        "monitor group size < $(group_size) => abort \"Group dissolved\"",
        "mgroup size=$(group_size) gear=best",
        "gm on",
        "wait group $(group_size) 180",
        "teleport $(instance_entry)",
        "wait 5",
        "teleport $(boss_destination)",
        "teleport group expect=$(group_size)",
        "wait 5",
        "clear except=$(boss_entry) radius500",
        "pull $(boss_entry)",
        "clear except=$(boss_entry) radius500",
        "$(start_command)",
        "wait 3",
        "gm off",
        "pull $(boss_entry)",
        "observe"};

    for (auto& destination : bossDestinations)
    {
        for (auto& point : destination->GetPoints())
        {
            if (!point->getMapEntry())
                continue;

            const MapEntry* mapEntry = point->getMapEntry();

            if (!mapEntry->IsDungeon())
                continue;

            const InstanceTemplate* instanceTemplate = point->getInstanceTemplate();
            if (!instanceTemplate)
                continue;

            CreatureInfo const* bossInfo = static_cast<BossTravelDestination*>(destination)->GetCreatureInfo();
            if (!bossInfo)
                continue;

            GuidPosition entry;
            std::string mapName = mapEntry->name[0];

            if (!ParseLocation(mapName, entry))
            {
                mapName.erase(remove_if(mapName.begin(), mapName.end(), isspace), mapName.end());
            }

            if (!ParseLocation(mapName, entry))
            {
                if (mapName.find(" ") != std::string::npos)
                    mapName = mapName.substr(0, mapName.find(" "));
            }

            if (!ResolveInstanceEntry(mapEntry, mapName, entry))
                continue;

            std::string startCommand = ".bot p @tank co + mark rti";
            std::string maxPlayers = "5";

            if (mapEntry->IsRaid())
            {
#if defined(MANGOSBOT_ZERO) || defined(MANGOSBOT_ONE)
                maxPlayers = std::to_string(instanceTemplate->maxPlayers);
#else
                if (MapDifficultyEntry const* mapDiff = GetMapDifficultyData(mapEntry->MapID, REGULAR_DIFFICULTY))
                    maxPlayers = std::to_string(mapDiff->maxPlayers);
                else
                    maxPlayers = "25";
#endif
                startCommand = ".bot r @tank co + mark rti";
            }

            std::string bossName = mapEntry->name[0] + std::string("_") + bossInfo->Name;
            std::replace(bossName.begin(), bossName.end(), ' ', '_');
            std::replace(bossName.begin(), bossName.end(), '\'', '_');
            std::transform(bossName.begin(), bossName.end(), bossName.begin(), ::tolower);

#ifdef MANTECH_RAID_LAB
            if (RaidLab::Enabled() && RaidLab::AllowedMap(mapEntry->MapID))
            {
                std::string approach = ComputeBossApproachCoords(mapEntry, *point, bossInfo->MinLevel, 60);
                const bool magmadar = mapEntry->MapID == 409 && bossInfo->Entry == 11982;
                const bool reviewedNaxxRoom=mapEntry->MapID==533 && (bossInfo->Entry==15956 || bossInfo->Entry==15953 || bossInfo->Entry==15952 || bossInfo->Entry==15931 || bossInfo->Entry==15936);
                const bool reviewedZgRoom=mapEntry->MapID==309 && (bossInfo->Entry==14510 || bossInfo->Entry==14509 || bossInfo->Entry==11380);
                const bool reviewedAqRoom=(mapEntry->MapID==509 && (bossInfo->Entry==15369 || bossInfo->Entry==15348)) ||
                    (mapEntry->MapID==531 && (bossInfo->Entry==15511 || bossInfo->Entry==15543 || bossInfo->Entry==15544));
                const bool reviewedBwlRoom=mapEntry->MapID==469 && bossInfo->Entry==12017;
                const std::vector<std::string> fixtures = magmadar
                    ? std::vector<std::string>{"", "_cleared_room", "_post_lucifron_cleared_room"} : mapEntry->MapID == 409 || reviewedNaxxRoom || reviewedZgRoom || reviewedAqRoom || reviewedBwlRoom
                    ? std::vector<std::string>{"", "_cleared_room"} : mapEntry->MapID==469
                    ? std::vector<std::string>{"","_prepared"}:std::vector<std::string>{""};
                for(const auto& fixture:fixtures) {
                const std::string staging = magmadar || fixture=="_cleared_room"
                    ? "raidlab staging " + std::to_string(bossInfo->Entry) + std::string(fixture.empty()?"":" cleared-room") :
                    mapEntry->MapID == 309 && bossInfo->Entry == 14517 ? "raidlab staging 14517" : "wait 1";
                const std::vector<std::string> modes=mapEntry->MapID==533 && bossInfo->Entry==15936 && fixture=="_cleared_room"
                    ? std::vector<std::string>{"bot","leader","leader_mobile"} : magmadar && fixture=="_post_lucifron_cleared_room"
                    ? std::vector<std::string>{"leader","leader_mobile"} : magmadar && fixture=="_cleared_room"
                    ? std::vector<std::string>{"bot","leader","leader_mobile"}:std::vector<std::string>{"bot","leader"};
                for (const std::string& mode : modes)
                    RegisterTest("raidlab_" + std::to_string(mapEntry->MapID) + "_" + std::to_string(bossInfo->Entry) + "_" + mode + fixture, {
                        "require bot is level=60",
                        "mgroup size=" + maxPlayers + " gear=best",
                        "wait group " + maxPlayers + " 180",
                        "gm on", "teleport " + mapName, "wait 5",
                        "teleport " + approach, "wait 5", staging, "wait 5",
                        "raidlab landing " + std::to_string(bossInfo->Entry), "wait 5",
                        mode!="bot"?"raidlab leader":"wait 1",
                        "teleport group expect=" + maxPlayers, "wait 5",mode!="bot"?"raidlab leader settled":"wait 1", "gm off",
                        fixture=="_prepared"?"raidlab provision bwl":"wait 1",
                        "raidlab " + std::to_string(bossInfo->Entry) + " " + (mode=="bot"?"bot":"leader"),
                        "monitor raidlab boss dead => pass \"Observed native boss death; mechanic coverage separate\"",
                        "monitor raidlab no engagement => fail \"Native boss did not engage after the ordinary pull\"",
                        "monitor time > 900 => fail \"Encounter timeout\"",
                        "monitor party wiped => fail \"Raid wiped\"",
                        "monitor not on map " + mapName + " => abort \"Leader left map\"",
                        "monitor group size < " + maxPlayers + " => abort \"Group lost members\"",
                        "observe"
                    });
                }
            }
#endif

            // Encounter tests drop the raid on the boss -> replaced by the approach point
            // (1.5x aggro radius from the boss, on the path toward an instance exit).
            RegisterInstanceScenario("scenario_boss_", bossName, bossEncounterTemplate, ScenarioParams{
                {"timeout_s",        "600"                                          },
                {"start_command",    startCommand                                   },
                {"group_size",       maxPlayers                                     },
                {"instance_entry",   mapName                                        },
                {"boss_entry",       std::to_string(bossInfo->Entry)                },
                {"boss_name",        bossInfo->Name                                 }
            }, instanceTemplate->levelMin, [&](ScenarioParams& leveled, uint32 botLevel)
            {
                leveled["boss_destination"] = ComputeBossApproachCoords(mapEntry, *point, bossInfo->MinLevel, botLevel);
            });
        }
    }
}

// BL-45 part 2: the layer-2 reach test. The trash template observes clearing, the encounter
// template teleports next to the boss and fights - but "enter the dungeon and TRAVEL to the boss
// (alive)" had no coverage. The reach template enters at the instance entry, sets the boss as the
// travel destination and passes when the party is near the boss while it is still alive.
void TestRegistry::GenerateBossReachTest()
{
    DestinationList bossDestinations = sTravelMgr.GetDestinations(PlayerTravelInfo(), (uint32)TravelDestinationPurpose::Boss, {}, false, 0);

    std::vector<std::string> bossReachTemplate = {
        "# reach boss test - enter instance, travel to the boss, party near boss with boss alive",
        "require bot is level=$(level)",
        "monitor distance to $(boss_location) < $(reach_dist) => pass \"Party reached $(boss_name) after <time elapsed>\"",
        "monitor mob $(boss_entry) is dead => fail \"Boss $(boss_name) died before the party reached it\"",
        "monitor time > $(timeout_s) => fail \"Timeout: boss not reached after <time elapsed> (traveled <distance traveled>)\"",
        "monitor party wiped => fail \"Party wiped on the way to $(boss_name)\"",
        "monitor bot dead => abort \"Bot died on the way to $(boss_name)\"",
        "monitor not on map $(instance_entry) => abort \"Bot left instance map\"",
        "monitor group size < 2 => abort \"Group dissolved\"",
        "mgroup size=$(group_size) gear=best",
        "gm visible on",
        "gm off",
        "wait group $(group_size) 180",
        "teleport $(instance_entry)",
        // BL-42 follow-up: see instanceGroupTemplate - abort honestly on a short group.
        "teleport group expect=$(group_size)",
        "wait 10",
        "$(start_command)",
        "set destination $(boss_destination)",
        "observe"};

    for (auto& destination : bossDestinations)
    {
        for (auto& point : destination->GetPoints())
        {
            if (!point->getMapEntry())
                continue;

            const MapEntry* mapEntry = point->getMapEntry();

            if (!mapEntry->IsDungeon())
                continue;

            const InstanceTemplate* instanceTemplate = point->getInstanceTemplate();
            if (!instanceTemplate)
                continue;

            CreatureInfo const* bossInfo = static_cast<BossTravelDestination*>(destination)->GetCreatureInfo();
            if (!bossInfo)
                continue;

            GuidPosition entry;
            std::string mapName = mapEntry->name[0];

            if (!ResolveInstanceEntry(mapEntry, mapName, entry))
                continue;

            std::string startCommand = ".bot p @tank co + mark rti";
            std::string maxPlayers = "5";

            if (mapEntry->IsRaid())
            {
#if defined(MANGOSBOT_ZERO) || defined(MANGOSBOT_ONE)
                maxPlayers = std::to_string(instanceTemplate->maxPlayers);
#else
                if (MapDifficultyEntry const* mapDiff = GetMapDifficultyData(mapEntry->MapID, REGULAR_DIFFICULTY))
                    maxPlayers = std::to_string(mapDiff->maxPlayers);
                else
                    maxPlayers = "25";
#endif
                startCommand = ".bot r @tank co + mark rti";
            }

            std::string bossName = mapEntry->name[0] + std::string("_") + bossInfo->Name;
            std::replace(bossName.begin(), bossName.end(), ' ', '_');
            std::replace(bossName.begin(), bossName.end(), 39, 95); // 39 = apostrophe, 95 = underscore
            std::transform(bossName.begin(), bossName.end(), bossName.begin(), ::tolower);

            RegisterNamedLocation(bossName, GuidPosition(ObjectGuid(), *point));

            RegisterInstanceScenario("scenario_reach_", bossName, bossReachTemplate, ScenarioParams{
                {"timeout_s",        "1800"                                         },
                {"start_command",    startCommand                                   },
                {"group_size",       maxPlayers                                     },
                {"reach_dist",       "60"                                           },
                {"instance_entry",   mapName                                        },
                {"boss_location",    bossName                                       },
                {"boss_destination", bossName                                       },
                {"boss_entry",       std::to_string(bossInfo->Entry)                },
                {"boss_name",        bossInfo->Name                                 }
            }, instanceTemplate->levelMin);
        }
    }
}
void TestRegistry::RegisterInstanceTests()
{
    GenerateBossWalkTest();
    GenerateBossEncounterTest();
    GenerateBossReachTest();
}
