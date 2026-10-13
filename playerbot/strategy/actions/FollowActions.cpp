
#include "playerbot/playerbot.h"
#include "playerbot/PartyCombatSupport.h"
#include "FollowActions.h"
#include "playerbot/PlayerbotAIConfig.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/strategy/values/Formations.h"
#include "playerbot/strategy/values/FreeMoveValues.h"
#include "playerbot/TravelMgr.h"
#include "playerbot/LootObjectStack.h"
#include "Movement/MoveSpline.h"

using namespace ai;

bool ai::RaidRestInProgress(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    if (!ai->HasRealPlayerMaster() || ai->IsRealPlayer() || !bot->GetGroup() ||
        !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->IsInCombat() || !bot->IsSitState())
        return false;

    // Drink/food are sitting auras after their instant cast. An idle formation
    // correction must not cancel them and start another consumable every tick.
    const bool drinking = bot->GetPower(POWER_MANA) < bot->GetMaxPower(POWER_MANA) && ai->HasAura("drink", bot);
    const bool eating = bot->GetHealth() < bot->GetMaxHealth() && ai->HasAura("food", bot);
    if ((!drinking && !eating) || !ai->GetMaster() || ai->GetMaster()->IsMoving() || GetPartyCombatAnchor(ai)) return false;
    Unit* target = ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("follow target")->Get());
    return target && ai->IsSafe(target) && target->IsAlive() && !target->IsMoving() &&
        bot->IsWithinDistInMap(target, sPlayerbotAIConfig.sightDistance);
}

bool ai::RaidRegroupNeeded(PlayerbotAI* ai)
{
    Player* bot = ai->GetBot();
    if (!ai->HasRealPlayerMaster() || ai->IsRealPlayer() || !bot->GetGroup() ||
        !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->IsInCombat() || ai->IsStateActive(BotState::BOT_STATE_COMBAT) || !ai->CanMove() ||
        !ai->HasStrategy("follow", BotState::BOT_STATE_NON_COMBAT) ||
        ai->HasStrategy("stay", BotState::BOT_STATE_NON_COMBAT) || ai->HasStrategy("guard", BotState::BOT_STATE_NON_COMBAT) ||
        bot->IsNonMeleeSpellCasted(false, false, true) || ai->IsJumping() || bot->IsTaxiFlying() ||
        (bot->movespline && !bot->movespline->Finalized()) || RaidRestInProgress(ai)) return false;
    Unit* target = ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("follow target")->Get());
    Formation* formation = ai->GetAiObjectContext()->GetValue<Formation*>("formation")->Get();
    if (!target || !ai->IsSafe(target) || !formation || !target->IsAlive() || !bot->IsInMap(target)) return false;
    const WorldLocation station = formation->GetLocation();
    return !Formation::IsNullLocation(station) && station.mapid == bot->GetMapId() &&
        bot->GetDistance(station.coord_x, station.coord_y, station.coord_z) > 3.0f;
}

bool FollowAction::Execute(Event& event)
{
    if (RaidRestInProgress(ai)) return false;
    bool moved = false;
    Unit* followTarget = ai->GetUnit(AI_VALUE(ObjectGuid, "follow target"));
    Formation* formation = AI_VALUE(Formation*, "formation");

    // Support the pull from casting range rather than hugging the tank.
    if (followTarget && ai->IsHeal(bot) && followTarget == GetPartyCombatAnchor(ai) &&
        !AI_VALUE(GuidPosition, "manual follow target"))
        return MoveTo(followTarget, std::max(10.0f, ai->GetRange("spell") - 5.0f));

    if (ai->IsSafe(followTarget))
    {
        if (formation)
        {
            WorldLocation loc = formation->GetLocation();
            if (!Formation::IsNullLocation(loc) && loc.mapid != -1)
            {
                moved = Follow(followTarget, formation->GetOffset(), formation->GetAngle());
            }
        }
    }
    else
        moved = Follow(followTarget, 0, 0);

    return moved;
}

bool FollowAction::isUseful()
{
    if (!ai->CanMove() || RaidRestInProgress(ai))
        return false;

    float distance = 0;
    Unit* followTarget = ai->GetUnit(AI_VALUE(ObjectGuid, "follow target"));
    Formation* formation = AI_VALUE(Formation*, "formation");

    if (followTarget && ai->IsHeal(bot) && followTarget == GetPartyCombatAnchor(ai) &&
        !AI_VALUE(GuidPosition, "manual follow target"))
        return !bot->IsWithinDistInMap(followTarget, std::max(10.0f, ai->GetRange("spell") - 5.0f)) ||
            !bot->IsWithinLOSInMap(followTarget);

    if (followTarget && followTarget->IsPlayer())
    {
        if (AI_VALUE(GuidPosition, "rpg target") && CanFreeMoveValue::CanFreeMoveTo(ai, AI_VALUE(GuidPosition, "rpg target")))
        {
            return false;
        }
    }

    if (followTarget)
    {
        if (followTarget->IsTaxiFlying() || !CanDeadFollow(followTarget) || followTarget->GetGUIDLow() == bot->GetGUIDLow())
        {
            return false;
        }
    }

    if (followTarget)
    {
#ifndef MANGOSBOT_ZERO
        if (bot->IsFreeFlying() || bot->IsFlying() || bot->IsSwimming())
            distance = sServerFacade.GetDistance(bot, followTarget);
        else
#endif
        distance = sServerFacade.GetDistance2d(bot, followTarget);
    }
    else
    {
        WorldLocation loc = formation->GetLocation();
        if (Formation::IsNullLocation(loc) || bot->GetMapId() != loc.mapid)
        {
            return false;
        }
#ifndef MANGOSBOT_ZERO
        if (bot->IsFreeFlying() || bot->IsFlying() || bot->IsSwimming())
            distance = sServerFacade.GetDistance(bot, loc.coord_x, loc.coord_y, loc.coord_z);
        else
#endif
        distance = sServerFacade.GetDistance2d(bot, loc.coord_x, loc.coord_y);
    }

    if (sServerFacade.IsDistanceGreaterThan(distance, sPlayerbotAIConfig.sightDistance))
    {
        return true;
    }

    // maybe jump is faster?
    if (ai->HasStrategy("follow jump", BotState::BOT_STATE_NON_COMBAT) && ai->AllowActivity())
    {
        return true;
    }

    if (followTarget && sServerFacade.GetChaseTarget(bot) && sServerFacade.GetChaseTarget(bot)->GetObjectGuid() == followTarget->GetObjectGuid() && formation->GetAngle() == sServerFacade.GetChaseAngle(bot) && formation->GetOffset() == sServerFacade.GetChaseOffset(bot))
    {
        return RaidRegroupNeeded(ai);
    }

    return true;
}

bool FollowAction::CanDeadFollow(Unit* target)
{
    //Move to corpse when dead and player is alive or not a ghost.
    if (!sServerFacade.IsAlive(bot) && (sServerFacade.IsAlive(target) || !target->HasFlag(PLAYER_FLAGS, PLAYER_FLAGS_GHOST)))
    {
        return false;
    }
    
    return true;
}

bool StopFollowAction::isUseful()
{
    if (bot->GetMotionMaster()->GetCurrentMovementGeneratorType() != FOLLOW_MOTION_TYPE)
        return false;

    if (sServerFacade.GetChaseTarget(bot) && !sServerFacade.GetChaseTarget(bot)->IsPlayer() && sServerFacade.GetChaseTarget(bot)->IsMoving())
        return false;

    return true;
}

bool FleeToMasterAction::Execute(Event& event)
{
    if (IsGenericRaidFleeBlocked()) return false;
    Player* requester = event.getOwner() ? event.getOwner() : GetMaster();
    Unit* fTarget = ai->GetUnit(AI_VALUE(ObjectGuid, "master target"));
    bool canFollow = Follow(fTarget);
    if (!canFollow)
    {
        //SetDuration(5000);
        return false;
    }

    WorldPosition targetPos(fTarget);
    WorldPosition bosPos(bot);
    float distance = bosPos.fDist(targetPos);


    uint32 scale = 5;
    if (bot->GetGroup() && bot->GetGroup()->GetMembersCount() > 5)
        scale = bot->GetGroup()->GetMembersCount();
        

    if (distance > sPlayerbotAIConfig.reactDistance && bot->IsInCombat())
    {
        if (!urand(0, scale))
            ai->TellPlayerNoFacing(requester, "I'm heading to your location but I'm in combat", PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL, false);
            //ai->TellPlayer(BOT_TEXT("wait_travel_combat"), PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL, false);
    }
    else if (distance < sPlayerbotAIConfig.reactDistance * 3)
    {
        if (!urand(0, scale))
            ai->TellPlayerNoFacing(requester, BOT_TEXT("wait_travel_close"), PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL, false);
    }
    else if (distance < 1000)
    {
        if (!urand(0, scale*4))
            ai->TellPlayerNoFacing(requester, BOT_TEXT("wait_travel_medium"), PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL, false);
    }
    else
        if (!urand(0, scale*6))
            ai->TellPlayerNoFacing(requester, BOT_TEXT("wait_travel_medium"), PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL, false);
           
    SetDuration(3000U);
    return true;
}

bool FleeToMasterAction::isUseful()
{
    if (IsGenericRaidFleeBlocked()) return false;
    if (!ai->CanMove())
        return false;

    if (!ai->GetGroupMaster())
        return false;

    if (ai->GetGroupMaster() == bot)
        return false;

    Unit* target = ai->GetUnit(AI_VALUE(ObjectGuid, "current target"));

    if (target && ai->GetGroupMaster()->HasTarget(target->GetObjectGuid()))
        return false;

    if (!(ai->HasStrategy("follow", BotState::BOT_STATE_NON_COMBAT) ||
      ai->HasStrategy("wander", BotState::BOT_STATE_NON_COMBAT)))
        return false;

    Unit* fTarget = ai->GetUnit(AI_VALUE(ObjectGuid, "master target"));
    
    if (!CanDeadFollow(fTarget))
        return false;

    if (fTarget && fTarget->IsPlayer())
    {
        if (AI_VALUE(GuidPosition, "rpg target") && CanFreeMoveValue::CanFreeMoveTo(ai, AI_VALUE(GuidPosition, "rpg target")))
            return false;
    }

    LootObject loot = AI_VALUE(LootObject, "loot target");
    if (loot.IsLootPossible(bot))
        return false;

    return true;
}

