
#include "playerbot/playerbot.h"
#include "PvpValues.h"
#include "BattleGround/BattleGroundWS.h"
#include "playerbot/ServerFacade.h"
#ifndef MANGOSBOT_ZERO
#include "BattleGround/BattleGroundEY.h"
#endif
#include "playerbot/TravelMgr.h"
#include "SharedValueContext.h"

using namespace ai;

std::list<CreatureDataPair const*> BgMastersValue::Calculate()
{
    BattleGroundTypeId bgTypeId = (BattleGroundTypeId)stoi(qualifier);

    std::vector<uint32> entries;
    std::map<Team, std::map<BattleGroundTypeId, std::list<uint32>>> battleMastersCache = sRandomPlayerbotMgr.getBattleMastersCache();
    entries.insert(entries.end(), battleMastersCache[TEAM_BOTH_ALLOWED][bgTypeId].begin(), battleMastersCache[TEAM_BOTH_ALLOWED][bgTypeId].end());
    entries.insert(entries.end(), battleMastersCache[ALLIANCE][bgTypeId].begin(), battleMastersCache[ALLIANCE][bgTypeId].end());
    entries.insert(entries.end(), battleMastersCache[HORDE][bgTypeId].begin(), battleMastersCache[HORDE][bgTypeId].end());

    std::list<CreatureDataPair const*> bmGuids;

    for (auto entry : entries)
    {
        for(auto creaturePair : WorldPosition().getCreaturesNear(0, entry))
        {
            bmGuids.push_back(creaturePair);
        }        
    }

    return bmGuids;
}

CreatureDataPair const* BgMasterValue::Calculate()
{
    CreatureDataPair const* bmPair = NearestBm(false);

    if (!bmPair)
        bmPair = NearestBm(true);
   
    return bmPair;
}

CreatureDataPair const* BgMasterValue::NearestBm(bool allowDead)
{
    WorldPosition botPos(bot);

    std::list<CreatureDataPair const*> bmPairs = GAI_VALUE2(std::list<CreatureDataPair const*>, "bg masters", qualifier);

    float rDist;
    CreatureDataPair const* rbmPair = nullptr;

    for (auto& bmPair : bmPairs)
    {
        if (!bmPair)
            continue;

        WorldPosition bmPos(bmPair);

        float dist = botPos.distance(bmPos); //This is the aproximate travel distance.

        // Skip battlemasters that are not on the same map
        if (bot->GetMapId() != bmPos.getMapId())
            continue;

        //Did we already find a closer unit that is not dead?
        if (rbmPair && rDist <= dist)
            continue;

        CreatureInfo const* bmTemplate = ObjectMgr::GetCreatureTemplate(bmPair->second.id);

        if (!bmTemplate)
            continue;

        FactionTemplateEntry const* bmFactionEntry = sFactionTemplateStore.LookupEntry(bmTemplate->Faction);
        if (!bmFactionEntry)
            continue;

        //Is the unit hostile?
        if (ai->getReaction(bmFactionEntry) < REP_NEUTRAL)
            continue;

        AreaTableEntry const* area = bmPos.GetArea();

        if (!area)
            continue;

        //Is the area hostile?
        if (area->team == 4 && bot->GetTeam() == ALLIANCE)
            continue;
        if (area->team == 2 && bot->GetTeam() == HORDE)
            continue;

        if (!allowDead)
        {
            Unit* unit = ai->GetUnit(bmPair);

            if (!unit)
                continue;

            //Is the unit dead?
            if (unit->GetDeathState() == DEAD)
                continue;
        }

        rbmPair = bmPair;
        rDist = dist;
    }

    return rbmPair;
}


BattleGroundTypeId RpgBgTypeValue::Calculate()
{
    GuidPosition guidPosition = AI_VALUE(GuidPosition, "rpg target");

    // check Deserter debuff
    if (!bot->CanJoinToBattleground())
        return BATTLEGROUND_TYPE_NONE;

    // check if has free queue slots
    if (!bot->HasFreeBattleGroundQueueId())
        return BATTLEGROUND_TYPE_NONE;

    if(guidPosition)
        for (uint32 i = 1; i < MAX_BATTLEGROUND_QUEUE_TYPES; i++)
        {
            BattleGroundQueueTypeId queueTypeId = (BattleGroundQueueTypeId)i;

            BattleGroundTypeId bgTypeId = sServerFacade.BgTemplateId(queueTypeId);

            BattleGround* bg = sBattleGroundMgr.GetBattleGroundTemplate(bgTypeId);
            if (!bg)
                continue;

            if (bot->GetLevel() < bg->GetMinLevel())
                continue;

            // check if already in queue
            if (bot->InBattleGroundQueueForBattleGroundQueueType(queueTypeId))
                continue;

            std::map<Team, std::map<BattleGroundTypeId, std::list<uint32>>> battleMastersCache = sRandomPlayerbotMgr.getBattleMastersCache();

            for (auto& entry : battleMastersCache[TEAM_BOTH_ALLOWED][bgTypeId])
                if (entry == guidPosition.GetEntry())
                    return bgTypeId;

            for (auto& entry : battleMastersCache[bot->GetTeam()][bgTypeId])
                if (entry == guidPosition.GetEntry())
                    return bgTypeId;
        }

    return BATTLEGROUND_TYPE_NONE;
}

Unit* FlagCarrierValue::Calculate()
{
    Unit* carrier = nullptr;

    if (ai->GetBot()->InBattleGround())
    {
        if (ActualBattlegroundType(bot) == BattleGroundTypeId::BATTLEGROUND_WS)
        {
            BattleGroundWS *bg = (BattleGroundWS*)ai->GetBot()->GetBattleGround();

            if (!bg)
                return nullptr;

            if ((!sameTeam && bot->GetTeam() == HORDE || (sameTeam && bot->GetTeam() == ALLIANCE)) && !bg->GetFlagCarrierGuid(TEAM_INDEX_HORDE).IsEmpty())
                carrier = bg->GetBgMap()->GetPlayer(bg->GetFlagCarrierGuid(TEAM_INDEX_HORDE));

            if ((!sameTeam && bot->GetTeam() == ALLIANCE || (sameTeam && bot->GetTeam() == HORDE)) && !bg->GetFlagCarrierGuid(TEAM_INDEX_ALLIANCE).IsEmpty())
                carrier = bg->GetBgMap()->GetPlayer(bg->GetFlagCarrierGuid(TEAM_INDEX_ALLIANCE));

            if (carrier)
            {
                if (ignoreRange || bot->IsWithinDistInMap(carrier, sPlayerbotAIConfig.sightDistance))
                {
                    return carrier;
                }
                else
                    return nullptr;
            }
        }
#ifndef MANGOSBOT_ZERO
        if (ActualBattlegroundType(bot) == BattleGroundTypeId::BATTLEGROUND_EY)
        {
            BattleGroundEY* bg = (BattleGroundEY*)ai->GetBot()->GetBattleGround();

            if (!bg)
                return nullptr;

            if (bg->GetFlagCarrierGuid().IsEmpty())
                return nullptr;

            Player* fc = bg->GetBgMap()->GetPlayer(bg->GetFlagCarrierGuid());
            if (!fc)
                return nullptr;

            if (!sameTeam && (fc->GetTeam() != bot->GetTeam()))
                carrier = fc;

            if (sameTeam && (fc->GetTeam() == bot->GetTeam()))
                carrier = fc;

            if (carrier)
            {
                if (ignoreRange || bot->IsWithinDistInMap(carrier, sPlayerbotAIConfig.sightDistance))
                {
                    return carrier;
                }
                else
                    return nullptr;
            }
        }
#endif
    }
    return carrier;
}

BattleGroundTypeId ai::ActualBattlegroundType(Player* player)
{
    BattleGround* bg = player ? player->GetBattleGround() : nullptr;
    if (!bg) return BATTLEGROUND_TYPE_NONE;
#ifdef MANGOSBOT_TWO
    if (bg->GetTypeId() == BATTLEGROUND_RB) return bg->GetTypeId(true);
#endif
    return bg->GetTypeId();
}

bool ai::IsBattlegroundFlagCarrier(Player* player)
{
    if (!player) return false;
    BattleGround* bg = player->GetBattleGround();
    if (ActualBattlegroundType(player) == BATTLEGROUND_WS)
    {
        BattleGroundWS* ws = static_cast<BattleGroundWS*>(bg);
        return ws->GetFlagCarrierGuid(TEAM_INDEX_ALLIANCE) == player->GetObjectGuid() ||
            ws->GetFlagCarrierGuid(TEAM_INDEX_HORDE) == player->GetObjectGuid();
    }
#ifndef MANGOSBOT_ZERO
    if (ActualBattlegroundType(player) == BATTLEGROUND_EY)
        return static_cast<BattleGroundEY*>(bg)->GetFlagCarrierGuid() == player->GetObjectGuid();
#endif
    return false;
}

// Limit threat recognition to nearby, observable combat. Selecting a player
// while fighting someone else is not by itself evidence of an attack.
bool ai::IsWarsongLocalThreat(PlayerbotAI* ai, Unit* enemy, Unit* protectedPlayer)
{
    if (!ai || !enemy || !protectedPlayer) return false;
    Player* bot = ai->GetBot();
    if (ActualBattlegroundType(bot) != BATTLEGROUND_WS || !enemy->IsInWorld() ||
        !enemy->IsAlive() || !protectedPlayer->IsInWorld() || !protectedPlayer->IsAlive() ||
        !bot->IsWithinDistInMap(enemy, 30.0f) || !bot->IsWithinDistInMap(protectedPlayer, 30.0f) ||
        !bot->IsWithinLOSInMap(enemy) || !enemy->IsInCombat() ||
        sServerFacade.IsFriendlyTo(bot, enemy)) return false;
    return enemy->GetVictim() == protectedPlayer ||
        (enemy->IsNonMeleeSpellCasted(false) && enemy->GetSelectionGuid() == protectedPlayer->GetObjectGuid());
}

// Use one eligible candidate set for automatic WSG attack and carrier actions.
// Native visibility, hostility, range and crowd-control filtering happens when
// constructing enemy player targets; no distant carrier is added around it.
Unit* ai::SelectWarsongCombatTarget(PlayerbotAI* ai)
{
    if (!ai || ActualBattlegroundType(ai->GetBot()) != BATTLEGROUND_WS || ai->HasRealPlayerMaster())
        return nullptr;
    Player* bot = ai->GetBot();
    AiObjectContext* context = ai->GetAiObjectContext();
    BattleGroundWS* bg = static_cast<BattleGroundWS*>(bot->GetBattleGround());
    if (bg->GetStatus() != STATUS_IN_PROGRESS) return nullptr;
    const ObjectGuid enemyCarrier = bg->GetFlagCarrierGuid(GetTeamIndexByTeamId(bot->GetTeam()));
    Unit* friendlyCarrier = bg->GetBgMap()->GetPlayer(bg->GetFlagCarrierGuid(
        GetTeamIndexByTeamId(bg->GetOtherTeam(bot->GetTeam()))));
    Unit* best = nullptr;
    int bestRank = 100, bestBand = 100;
    float bestHealth = 101.0f;
    const std::list<ObjectGuid> candidates = AI_VALUE(std::list<ObjectGuid>, "enemy player targets");
    for (const ObjectGuid& guid : candidates)
    {
        Unit* enemy = ai->GetUnit(guid);
        if (!enemy || !enemy->IsInWorld() || !enemy->IsAlive() || !bot->IsInMap(enemy) ||
            sServerFacade.IsFriendlyTo(bot, enemy)) continue;
        const int rank = guid == enemyCarrier ? 0 :
            (IsWarsongLocalThreat(ai, enemy, friendlyCarrier) || IsWarsongLocalThreat(ai, enemy, bot)) ? 1 : 2;
        const int band = static_cast<int>(sServerFacade.GetDistance2d(bot, enemy) / 10.0f);
        const float health = enemy->GetHealthPercent();
        if (!best || rank < bestRank || (rank == bestRank &&
            (band < bestBand || (band == bestBand && (health < bestHealth ||
                (health == bestHealth && guid < best->GetObjectGuid()))))))
        {
            best = enemy; bestRank = rank; bestBand = band; bestHealth = health;
        }
    }
    return best;
}

WarsongObjective WarsongObjectiveValue::Calculate()
{
    AiObjectContext* context = ai->GetAiObjectContext();
    WarsongObjective result;
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() ||
        ActualBattlegroundType(bot) != BATTLEGROUND_WS)
        return result;
    BattleGroundWS* bg = static_cast<BattleGroundWS*>(bot->GetBattleGround());
    if (bg->GetStatus() != STATUS_IN_PROGRESS) return result;
    const Team ownTeam = bot->GetTeam();
    const Team enemyTeam = bg->GetOtherTeam(ownTeam);
    auto flagState = [bg](Team team)
    {
        switch (bg->GetFlagState(team))
        {
            case BG_WS_FLAG_STATE_ON_PLAYER: return WarsongFlagState::Carried;
            case BG_WS_FLAG_STATE_ON_GROUND: return WarsongFlagState::Dropped;
            default: return WarsongFlagState::Base;
        }
    };

    // The same roster ordering gives bots stable jobs. Death does not reshuffle
    // jobs; roster changes can. Healers get the first escort/return slots.
    std::vector<Player*> roster;
    for (const auto& entry : bg->GetPlayers())
    {
        Player* member = bg->GetBgMap()->GetPlayer(entry.first);
        if (!member || !member->IsInWorld()) continue;
        if (entry.second.playerTeam != ownTeam)
        {
            if (IsWarsongLocalThreat(ai, member, bot)) result.pressured = true;
            continue;
        }
        PlayerbotAI* memberAI = member->GetPlayerbotAI();
        if (memberAI && !memberAI->IsRealPlayer() && !memberAI->HasRealPlayerMaster())
            roster.push_back(member);
    }
    if (std::find(roster.begin(), roster.end(), bot) == roster.end()) roster.push_back(bot);
    std::sort(roster.begin(), roster.end(), [this](Player* a, Player* b)
    {
        const bool healA = ai->IsHeal(a), healB = ai->IsHeal(b);
        return healA != healB ? healA : a->GetObjectGuid() < b->GetObjectGuid();
    });
    const size_t slot = std::distance(roster.begin(), std::find(roster.begin(), roster.end(), bot));
    const bool support = slot < (roster.size() + 2) / 3;
    result.carrying = IsBattlegroundFlagCarrier(bot);
    result.goal = SelectWarsongGoal(flagState(ownTeam), flagState(enemyTeam), result.carrying,
        support, roster.size() == 1);

    if (result.goal == WarsongGoal::Intercept || result.goal == WarsongGoal::Escort)
    {
        const Team flagTeam = result.goal == WarsongGoal::Intercept ? ownTeam : enemyTeam;
        result.target = bg->GetFlagCarrierGuid(GetTeamIndexByTeamId(flagTeam));
        Player* carrier = bg->GetBgMap()->GetPlayer(result.target);
        if (carrier && carrier->IsInWorld() && carrier->IsAlive() && bot->IsInMap(carrier))
            result.position.Set(carrier->GetPositionX(), carrier->GetPositionY(), carrier->GetPositionZ(), bot->GetMapId());
        else result.goal = WarsongGoal::None; // state transition: retry next sample
    }
    else if (result.goal == WarsongGoal::Return || result.goal == WarsongGoal::Recover)
    {
        const Team flagTeam = result.goal == WarsongGoal::Return ? ownTeam : enemyTeam;
        result.target = bg->GetDroppedFlagGuid(flagTeam);
        GameObject* flag = bg->GetBgMap()->GetGameObject(result.target);
        if (flag && flag->IsInWorld() && sServerFacade.isSpawned(flag))
            result.position.Set(flag->GetPositionX(), flag->GetPositionY(), flag->GetPositionZ(), bot->GetMapId());
        else result.goal = WarsongGoal::None; // don't send bots to an empty base
    }
    // Escorts may peel for a nearby carrier even when nobody is attacking the
    // escort. Beyond this leash they close the distance instead of chasing.
    if (result.goal == WarsongGoal::Escort)
    {
        Unit* carrier = bg->GetBgMap()->GetPlayer(result.target);
        const std::list<ObjectGuid> enemies = AI_VALUE(std::list<ObjectGuid>, "enemy player targets");
        for (const ObjectGuid& guid : enemies)
            if (IsWarsongLocalThreat(ai, ai->GetUnit(guid), carrier)) { result.pressured = true; break; }
    }
    return result;
}

bool ai::ShouldAdvanceWarsongObjective(PlayerbotAI* ai)
{
    if (!ai) return false;
    Player* bot = ai->GetBot();
    if (!bot || ActualBattlegroundType(bot) != BATTLEGROUND_WS) return false;
    AiObjectContext* context = ai->GetAiObjectContext();
    const WarsongObjective objective = AI_VALUE(WarsongObjective, "warsong objective");
    PositionEntry pos = AI_VALUE(PositionMap&, "position")["bg objective"];
    if (objective.goal == WarsongGoal::None || !pos.isSet() || pos.mapId != bot->GetMapId()) return false;
    const float distance = std::sqrt(bot->GetDistance(pos.x, pos.y, pos.z, DIST_CALC_NONE));
    if (objective.carrying) return distance > 3.0f;
    // Engage at the objective and defend against immediate pressure, but do not
    // let a lingering combat flag strand runners in unrelated midfield fights.
    return !ai->HasRealPlayerMaster() && !objective.pressured && distance > 15.0f &&
        bot->GetHealthPercent() > sPlayerbotAIConfig.lowHealth;
}
