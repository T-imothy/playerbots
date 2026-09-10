
#include "playerbot/playerbot.h"
#include "UseMeetingStoneAction.h"
#include "playerbot/BotRecruitment.h"
#include "RitualSummonAction.h"
#include "playerbot/PlayerbotAIConfig.h"
#include "playerbot/ServerFacade.h"

#include "BattleGround/BattleGround.h"
#include "BattleGround/BattleGroundMgr.h"
#include "LFG/LFGQueue.h"

#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

#include "playerbot/strategy/values/PositionValue.h"

using namespace MaNGOS;

bool UseMeetingStoneAction::Execute(Event& event)
{
    Player* requester = event.getOwner() ? event.getOwner() : GetMaster();
    if (!requester)
        return false;

    WorldPacket p(event.getPacket());
    p.rpos(0);
    ObjectGuid guid;
    p >> guid;

	if (requester->GetSelectionGuid() && requester->GetSelectionGuid() != bot->GetObjectGuid())
		return false;

	if (!requester->GetSelectionGuid() && requester->GetGroup() != bot->GetGroup())
		return false;

    if (requester->IsBeingTeleported())
        return false;

    if (sServerFacade.IsInCombat(bot))
    {
        ai->TellPlayerNoFacing(requester, "I am in combat");
        return false;
    }

    Map* map = requester->GetMap();
    if (!map)
        return false;

    GameObject *gameObject = map->GetGameObject(guid);
    if (!gameObject)
        return false;

	const GameObjectInfo* goInfo = gameObject->GetGOInfo();
	if (!goInfo || goInfo->type != GAMEOBJECT_TYPE_SUMMONING_RITUAL)
        return false;

    // A player's ritual click is not a convenience-teleport command. Participate
    // locally through the native object-use handler; the recipient waits for
    // the core's completed summon request and normal accept/decline handling.
    AssistSummoningRitualAction assist(ai);
    return assist.UseRitual(gameObject);
}

class AnyGameObjectInObjectRangeCheck
{
public:
    AnyGameObjectInObjectRangeCheck(WorldObject const* obj, float range) : i_obj(obj), i_range(range) {}
    WorldObject const& GetFocusObject() const { return *i_obj; }
    bool operator()(GameObject* u)
    {
        if (u && i_obj->IsWithinDistInMap(u, i_range) && sServerFacade.isSpawned(u) && u->GetGOInfo())
            return true;

        return false;
    }

private:
    WorldObject const* i_obj;
    float i_range;
};

bool SummonAction::Execute(Event& event)
{
    Player* requester = event.getOwner() ? event.getOwner() : GetMaster();
    if (requester && requester->isRealPlayer())
        return BotRecruitment::Queue(requester, bot, "summon");
    return ExecuteImmediate(event);
}

bool SummonAction::ExecuteImmediate(Event& event)
{
    Player* requester = event.getOwner() ? event.getOwner() : GetMaster();
    if (!requester || !requester->IsInWorld() || requester->IsBeingTeleported())
        return false;

    if (requester->GetSession()->GetSecurity() > SEC_PLAYER || sPlayerbotAIConfig.nonGmFreeSummon)
        return Teleport(requester, requester, bot);

    if(bot->GetMapId() == requester->GetMapId() && !WorldPosition(bot).canPathTo(requester, bot) && bot->GetDistance(requester) < sPlayerbotAIConfig.sightDistance) //We can't walk to requester so fine to short-range teleport.
        return Teleport(requester, requester, bot);

    if (SummonUsingGos(requester, requester, bot) || SummonUsingNpcs(requester, requester, bot))
    {
        ai->TellPlayerNoFacing(requester, BOT_TEXT("hello"));
        return true;
    }

    return false;
}

bool SummonAction::SummonUsingGos(Player* requester, Player *summoner, Player *player)
{
    std::list<GameObject*> targets;
    AnyGameObjectInObjectRangeCheck u_check(summoner, sPlayerbotAIConfig.sightDistance);
    GameObjectListSearcher<AnyGameObjectInObjectRangeCheck> searcher(targets, u_check);
    Cell::VisitAllObjects((const WorldObject*)summoner, searcher, sPlayerbotAIConfig.sightDistance);

    for(std::list<GameObject*>::iterator tIter = targets.begin(); tIter != targets.end(); ++tIter)
    {
        GameObject* go = *tIter;
        if (go && sServerFacade.isSpawned(go) && go->GetGoType() == GAMEOBJECT_TYPE_MEETINGSTONE)
            return Teleport(requester, summoner, player);
    }

    // This is a location probe: an innkeeper can still satisfy the request.
    // Do not announce failure before trying the other supported route.
    return false;
}

bool SummonAction::SummonUsingNpcs(Player* requester, Player *summoner, Player *player)
{
    if (!sPlayerbotAIConfig.summonAtInnkeepersEnabled)
        return false;

    // The bare summon command is only allowed to move the bot to its
    // requester.  Never consume a real player's hearthstone cooldown as an
    // implicit reverse-summon fallback.
    if (player->isRealPlayer())
        return false;

    std::list<Unit*> targets;
    AnyUnitInObjectRangeCheck u_check(summoner, sPlayerbotAIConfig.sightDistance);
    UnitListSearcher<AnyUnitInObjectRangeCheck> searcher(targets, u_check);
    Cell::VisitAllObjects(summoner, searcher, sPlayerbotAIConfig.sightDistance);
    for(std::list<Unit*>::iterator tIter = targets.begin(); tIter != targets.end(); ++tIter)
    {
        Unit* unit = *tIter;
        if (unit && unit->HasFlag(UNIT_NPC_FLAGS, UNIT_NPC_FLAG_INNKEEPER))
        {
            // A convenience summon is not a hearthstone cast. Neither require
            // the item/readiness nor create or clear its genuine cooldown.
            return Teleport(requester, summoner, player);
        }
    }

    ai->TellPlayerNoFacing(requester, summoner == bot ? "There are no innkeepers nearby" : "There are no innkeepers near you");
    return false;
}

void SummonAction::CancelAutonomousQueues()
{
    // Cancel only the bot's own queue entries, never the requester's group queue.
    ObjectGuid const guid = bot->GetObjectGuid();
#ifdef MANGOSBOT_ZERO
    sWorld.GetLFGQueue().GetMessager().AddMessage([guid](LFGQueue* queue)
    {
        queue->RemovePlayerFromQueue(guid, PLAYER_CLIENT_LEAVE);
    });
#elif defined(MANGOSBOT_ONE)
    sWorld.GetLFGQueue().GetMessager().AddMessage([guid](LFGQueue* queue)
    {
        queue->StopLookingForGroup(guid, guid);
    });
#else
    if (!bot->GetGroup())
        bot->GetLfgData().SetState(LFG_STATE_NONE);
    sWorld.GetLFGQueue().GetMessager().AddMessage([guid](LFGQueue* queue)
    {
        queue->RemoveFromQueue(guid);
    });
#endif
    for (uint32 slot = 0; slot < PLAYER_MAX_BATTLEGROUND_QUEUES; ++slot)
    {
        BattleGroundQueueTypeId const queue = bot->GetBattleGroundQueueTypeId(slot);
        if (queue == BATTLEGROUND_QUEUE_NONE)
            continue;
        BattleGroundTypeId const type = sBattleGroundMgr.BgTemplateId(queue);
        // The native teleport removes active BG membership when leaving its map.
        if (bot->InBattleGround() && type == bot->GetBattleGroundTypeId())
            continue;
        WorldPacket leave(CMSG_BATTLEFIELD_PORT, 20);
#ifdef MANGOSBOT_ZERO
        BattleGround* bg = sBattleGroundMgr.GetBattleGroundTemplate(type);
        if (!bg)
            continue;
        leave << uint32(bg->GetMapId()) << uint8(0);
#else
        leave << uint8(sBattleGroundMgr.BgArenaType(queue)) << uint8(0) << uint32(type) << uint16(0) << uint8(0);
#endif
        bot->GetSession()->HandleBattlefieldPortOpcode(leave);
    }
}

bool SummonAction::Teleport(Player* requester, Player *summoner, Player *player)
{
    if (!requester || !summoner || !player || player != bot || player->isRealPlayer() ||
        !summoner->IsInWorld() || !player->IsInWorld() ||
        !summoner->GetSession() || !player->GetSession() ||
        summoner->GetSession()->isLogingOut() || player->GetSession()->isLogingOut())
        return false;

    // Never attach a passenger manually after starting a far teleport. That
    // mixes world coordinates with transport offsets before the worldport ACK.
    if (summoner->GetTransport() || summoner->IsTaxiFlying())
    {
        ai->TellPlayerNoFacing(requester, "Your destination is moving on a flight or transport. Summon me again after you disembark.");
        return false;
    }

    // A near teleport cannot transfer between two instances of the same map.
    // Let the regular instance-entry/transition system handle that case.
    if (summoner->GetMapId() == player->GetMapId() && summoner->GetMap() != player->GetMap() &&
        summoner->GetMap()->Instanceable())
        return false;
    if (summoner->GetMap() != player->GetMap() && !summoner->GetMap()->CanEnter(player))
        return false;

    if (!summoner->IsBeingTeleported() && !player->IsBeingTeleported() && summoner != player)
    {
        float followAngle = GetFollowAngle();
        for (double angle = followAngle - M_PI; angle <= followAngle + M_PI; angle += M_PI / 4)
        {
            uint32 mapId = summoner->GetMapId();
            float x = summoner->GetPositionX() + cos(angle) * ai->GetRange("follow");
            float y = summoner->GetPositionY() + sin(angle) * ai->GetRange("follow");
            float z = summoner->GetPositionZ();
            summoner->UpdateGroundPositionZ(x, y, z);

            if (!summoner->IsWithinLOS(x, y, z + player->GetCollisionHeight(), true))
            {
                x = summoner->GetPositionX();
                y = summoner->GetPositionY();
                z = summoner->GetPositionZ();
            }

            if (summoner->IsWithinLOS(x, y, z + player->GetCollisionHeight(), true))
            {
                bool const revive = sServerFacade.UnitIsDead(player);

                // Only the explicitly summoned bot is interrupted. Native cleanup
                // restores possession/mover and taxi state; TeleportTo detaches a
                // transport passenger and handles combat, pets and BG departure.
                player->BreakCharmIncoming();
                player->BreakCharmOutgoing();
                if (player->HasCharmer())
                {
                    ai->TellPlayerNoFacing(requester, "The server could not release my controlling charm.");
                    return false;
                }
                if (!player->TaxiFlightInterrupt() && player->IsTaxiFlying())
                    player->OnTaxiFlightEject();
                player->InterruptNonMeleeSpells(false);

                // Combat does not block an explicit convenience summon. The native
                // teleport stops the summoned bot's combat; the requester stays in combat.
                // TeleportTo owns access checks, pets and transfer state. True
                // means accepted (possibly delayed), not a completed worldport.
                if (!player->TeleportTo(mapId, x, y, z, summoner->GetOrientation()))
                {
                    ai->TellPlayerNoFacing(requester, "The server refused the summon destination.");
                    return false;
                }
                CancelAutonomousQueues();
                if (!summoner->InBattleGround())
                    ai->ChangeStrategy("-lfg,-bg", BotState::BOT_STATE_NON_COMBAT);
                if (revive)
                    ai->QueueSummonRevival(mapId, x, y, z, summoner->GetInstanceId());
                player->GetMotionMaster()->Clear();
                    
                if(ai->HasStrategy("stay", BotState::BOT_STATE_NON_COMBAT))
                    SET_AI_VALUE2(PositionEntry, "pos", "stay", PositionEntry(x, y, z, mapId));
                if (ai->HasStrategy("guard", BotState::BOT_STATE_NON_COMBAT))
                    SET_AI_VALUE2(PositionEntry, "pos", "guard", PositionEntry(x, y, z, mapId));

                return true;
            }
        }
    }

    if(summoner != player)
        ai->TellPlayerNoFacing(requester, "Not enough place to summon");
    return false;
}

bool AcceptSummonAction::Execute(Event& event)
{
    WorldPacket p(event.getPacket());
    p.rpos(0);
    ObjectGuid summonerGuid;
    p >> summonerGuid;

    WorldPacket response(CMSG_SUMMON_RESPONSE);
    response << summonerGuid;
#if defined(MANGOSBOT_ONE) || defined(MANGOSBOT_TWO)
    response << uint8(1);
#endif
    bot->GetSession()->HandleSummonResponseOpcode(response);
    
    return true;
}
