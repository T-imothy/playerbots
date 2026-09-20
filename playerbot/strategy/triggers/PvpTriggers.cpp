
#include "playerbot/playerbot.h"
#include "BattleGroundTG.h"
#include "PvpTriggers.h"
#include "playerbot/strategy/values/PvpValues.h"
#include "playerbot/ServerFacade.h"
#include "Battlegrounds/BattleGroundWS.h"
#include "playerbot/strategy/values/PositionValue.h"
#ifndef MANGOSBOT_ZERO
#include "BattleGround/BattleGroundEY.h"
#endif

using namespace ai;

namespace
{
    // WSG's flag arrays are indexed by the flag's OWNING team: index
    // TEAM_INDEX_ALLIANCE is the Silverwing (Alliance) flag, and only a Horde
    // player can ever be carrying it. So the only flag a bot can hold is the
    // enemy team's flag.
    bool BotCarriesEnemyFlag(Player* bot, BattleGroundWS* bg)
    {
        const Team enemyTeam = BattleGround::GetOtherTeam(bot->GetTeam());
        if (bg->GetFlagState(enemyTeam) != BG_WS_FLAG_STATE_ON_PLAYER)
            return false;

        return bot->GetObjectGuid() == bg->GetFlagCarrierGuid(BattleGround::GetTeamIndexByTeamId(enemyTeam));
    }
}

bool EnemyPlayerNear::IsActive()
{
    // Check if we have any enemy players to attack
    if(AI_VALUE(bool, "has enemy player targets"))
    {
        Unit* currentTarget = ai->GetUnit(AI_VALUE(ObjectGuid, "current target"));
        if (currentTarget)
        {
            // Check if we have a better enemy player to attack
            Player* currentPlayerTarget = dynamic_cast<Player*>(currentTarget);
            if(currentPlayerTarget)
            {
                return currentPlayerTarget != ai->GetUnit(AI_VALUE(ObjectGuid, "enemy player target"));
            }
        }

        return true;
    }

    return false;
}

bool PlayerHasNoFlag::IsActive()
{
    return ActualBattlegroundType(bot) == BATTLEGROUND_WS && !IsBattlegroundFlagCarrier(bot);
}

bool PlayerIsInBattleground::IsActive()
{
    return ai->GetBot()->InBattleGround();
}

bool BgWaitingTrigger::IsActive()
{
    if (bot->InBattleGround())
    {
        if (bot->GetBattleGround() && bot->GetBattleGround()->GetStatus() == STATUS_WAIT_JOIN)
            return true;
    }
    return false;
}

bool BgActiveTrigger::IsActive()
{
    if (bot->InBattleGround())
    {
        if (bot->GetBattleGround() && bot->GetBattleGround()->GetStatus() == STATUS_IN_PROGRESS)
            return true;
    }
    return false;
}

bool BgInviteActiveTrigger::IsActive()
{
    if (bot->InBattleGround() || !bot->InBattleGroundQueue())
    {
        return false;
    }

    for (int i = 0; i < PLAYER_MAX_BATTLEGROUND_QUEUES; ++i)
    {
        BattleGroundQueueTypeId queueTypeId = bot->GetBattleGroundQueueTypeId(i);
        if (queueTypeId == BATTLEGROUND_QUEUE_NONE)
            continue;
#ifdef MANGOSBOT_TWOx
        BattleGroundQueue& bgQueue = sServerFacade.bgQueue(queueTypeId);
        GroupQueueInfo ginfo;
        if (bgQueue.GetPlayerGroupInfoData(bot->GetObjectGuid(), &ginfo))
        {
            if (ginfo.isInvitedToBgInstanceGuid && ginfo.removeInviteTime)
            {
                sLog.outDetail("Bot #%d <%s> (%u %s) : Invited to BG but not in BG", bot->GetGUIDLow(), bot->GetName(), bot->GetLevel(), bot->GetTeam() == ALLIANCE ? "A" : "H");
                return true;
            }
        }
#endif
#ifndef MANGOSBOT_ZERO
        if (bot->IsInvitedForBattleGroundQueueType(queueTypeId))
            return true;
#endif
    }
    return false;
}

bool BgEndedTrigger::IsActive()
{
    if (bot->InBattleGround())
    {
        if (bot->GetBattleGround() && bot->GetBattleGround()->GetStatus() == STATUS_WAIT_LEAVE)
            return true;
    }
    return false;
}

bool PlayerIsInBattlegroundWithoutFlag::IsActive()
{
    return bot->InBattleGround() && !IsBattlegroundFlagCarrier(bot);
}

bool PlayerHasFlag::IsActive()
{
    return IsBattlegroundFlagCarrier(bot);
}

bool TeamHasFlag::IsActive()
{
    if (ActualBattlegroundType(bot) != BATTLEGROUND_WS || IsBattlegroundFlagCarrier(bot)) return false;
    BattleGroundWS* bg = static_cast<BattleGroundWS*>(bot->GetBattleGround());
    return !bg->GetFlagCarrierGuid(GetTeamIndexByTeamId(bg->GetOtherTeam(bot->GetTeam()))).IsEmpty();
}

bool EnemyTeamHasFlag::IsActive()
{
    if (ActualBattlegroundType(bot) != BATTLEGROUND_WS) return false;
    BattleGroundWS* bg = static_cast<BattleGroundWS*>(bot->GetBattleGround());
    return !bg->GetFlagCarrierGuid(GetTeamIndexByTeamId(bot->GetTeam())).IsEmpty();
}

bool EnemyFlagCarrierNear::IsActive()
{
    Unit* carrier = ai->GetUnit(AI_VALUE(ObjectGuid, "enemy flag carrier"));
    return carrier && sServerFacade.IsDistanceLessOrEqualThan(sServerFacade.GetDistance2d(bot, carrier), VISIBILITY_DISTANCE_SMALL);
}

bool TeamFlagCarrierNear::IsActive()
{
    Unit* carrier = ai->GetUnit(AI_VALUE(ObjectGuid, "team flag carrier"));
    return carrier && sServerFacade.IsDistanceLessOrEqualThan(sServerFacade.GetDistance2d(bot, carrier), VISIBILITY_DISTANCE_SMALL);
}

bool PlayerWantsInBattlegroundTrigger::IsActive()
{
    if (bot->InBattleGround())
        return false;

    if (bot->GetBattleGround() && bot->GetBattleGround()->GetStatus() == STATUS_WAIT_JOIN)
        return false;

    if (bot->GetBattleGround() && bot->GetBattleGround()->GetStatus() == STATUS_IN_PROGRESS)
        return false;

    if (!bot->CanJoinToBattleground())
        return false;

    return true;
};

bool VehicleNearTrigger::IsActive()
{
    std::list<ObjectGuid> npcs = AI_VALUE(std::list<ObjectGuid>, "nearest vehicles");
    return npcs.size();
}

bool InVehicleTrigger::IsActive()
{
    return ai->IsInVehicle(false,false,false,false,false, getQualifier());
}

#ifdef MANGOSBOT_ZERO
bool ThornFlagDelivery::IsActive()
{
    BattleGround* bg = bot->GetBattleGround();
    if (!bg || bg->GetTypeId() != BATTLEGROUND_TG ||
        bg->GetStatus() != STATUS_IN_PROGRESS ||
        bg->GetFlagCarrierGuid() != bot->GetObjectGuid() ||
        !bot->HasAura(59005) || bot->IsNonMeleeSpellCasted(false)) return false;
    float x = 0, y = 0, z = 0;
    return static_cast<BattleGroundTG*>(bg)->GetObjective(bot, x, y, z) &&
        !bot->IsWithinDist3d(x, y, z, 3.0f);
}
bool ThornObjectiveTravel::IsActive()
{
    BattleGround* bg = bot->GetBattleGround();
    if (!bg || bg->GetTypeId() != BATTLEGROUND_TG || bg->GetStatus() != STATUS_IN_PROGRESS ||
        bg->GetFlagCarrierGuid() == bot->GetObjectGuid() || bot->IsNonMeleeSpellCasted(false)) return false;
    float x=0, y=0, z=0;
    if (!static_cast<BattleGroundTG*>(bg)->GetObjective(bot,x,y,z) ||
        bot->IsWithinDist3d(x,y,z,20.0f)) return false;
    // Fight nearby opponents around the assignment. Once a chase has taken us
    // more than 45 yards away, resume the assignment; survival still outranks us.
    Unit* victim = bot->GetVictim();
    if (!victim) victim = ai->GetUnit(AI_VALUE(ObjectGuid, "enemy player target"));
    if (victim && bot->IsWithinDistInMap(victim,12.0f) && bot->IsWithinLOSInMap(victim) &&
        bot->IsWithinDist3d(x,y,z,45.0f)) return false;
    return true;
}
bool ThornCarrierIntercept::IsActive()
{
    BattleGround* bg = bot->GetBattleGround();
    if (!bg || bg->GetTypeId() != BATTLEGROUND_TG || bg->GetStatus() != STATUS_IN_PROGRESS ||
        bg->GetFlagCarrierGuid() == bot->GetObjectGuid() || bot->IsNonMeleeSpellCasted(false)) return false;
    Unit* carrier = ai->GetUnit(AI_VALUE(ObjectGuid, "enemy flag carrier"));
    if (!carrier || !bot->IsWithinDistInMap(carrier, 35.0f)) return false;
    float x=0, y=0, z=0;
    // Interceptors are assigned to the carrier; other roles defend their nearby
    // objective instead of following the carrier away indefinitely.
    return static_cast<BattleGroundTG*>(bg)->GetObjective(bot,x,y,z) &&
        carrier->IsWithinDist3d(x,y,z,45.0f);
}
#endif
