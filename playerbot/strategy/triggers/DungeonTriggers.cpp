
#include "playerbot/playerbot.h"
#include "DungeonTriggers.h"
#include "playerbot/strategy/values/PositionValue.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/HazardsValue.h"
#include "playerbot/strategy/actions/MovementActions.h"
#include "playerbot/strategy/actions/DungeonActions.h"
#include "playerbot/strategy/actions/TempestKeepActions.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;
bool RotatingBeamTrigger::IsActive()
{
    return RotatingBeamAction(ai).isUseful();
}

bool VashjCoreTrigger::IsActive()
{
    return VashjCoreAction(ai).isUseful();
}

bool InnerDemonTrigger::IsActive()
{
    InnerDemonAction action(ai);
    return action.isUseful();
}


bool HeiganDanceTrigger::IsActive()
{
    HeiganDanceAction action(ai);
    return action.isUseful();
}

bool NajentusSpineTrigger::IsActive()
{
    NajentusSpineAction action(ai);
    return action.isUseful();
}

bool NajentusShieldTrigger::IsActive()
{
    NajentusShieldAction action(ai);
    return action.isUseful();
}

bool ArchimondeTearsTrigger::IsActive()
{
    ArchimondeTearsAction action(ai);
    return action.isUseful();
}

bool LinkedBurstTrigger::IsActive()
{
    LinkedBurstAction action(ai);
    return action.isUseful();
}

bool AkilzonStormTrigger::IsActive()
{
    AkilzonStormAction action(ai);
    return action.isUseful();
}

bool ColdMovementTrigger::IsActive()
{
    ColdMovementAction action(ai);
    return action.isUseful();
}

bool TharonjaSkeletonTrigger::IsActive()
{
    return TharonjaSkeletonAction(ai).isUseful();
}

bool ViscidusFrostTrigger::IsActive()
{
    ViscidusFrostAction action(ai);
    return action.isUseful();
}

bool MoamManaControlTrigger::IsActive()
{
    MoamManaControlAction action(ai);
    return action.isUseful();
}

bool HakkarPoisonTrigger::IsActive()
{
    HakkarPoisonAction action(ai);
    return action.isUseful();
}

bool OssirianCrystalTrigger::IsActive()
{
    OssirianCrystalAction action(ai);
    return action.isUseful();
}

bool BossCoverTrigger::IsActive()
{
    BossCoverAction action(ai);
    return action.isUseful();
}

bool DungeonAddTargetTrigger::IsActive()
{
    DungeonAddTargetAction action(ai);
    return action.isUseful();
}

bool SolarianPositionTrigger::IsActive()
{
    SolarianPositionAction action(ai);
    return action.isUseful();
}

bool SolarianPriorityTargetTrigger::IsActive()
{
    SolarianPriorityTargetAction action(ai);
    return action.isUseful();
}

bool MagtheridonCubeTrigger::IsActive()
{
    MagtheridonCubeAction action(ai);
    return action.isUseful();
}

bool GruulSpreadTrigger::IsActive()
{
    GruulSpreadAction action(ai);
    return action.isUseful();
}

bool BossCastPositionTrigger::IsActive()
{
    BossCastPositionAction action(ai);
    return action.isUseful();
}

bool EnterDungeonTrigger::IsActive()
{
    // Don't trigger if strategy already set
    if (!ai->HasStrategy(dungeonStrategy, BotState::BOT_STATE_COMBAT))
    {
        // If the bot is ready
        if (bot->IsInWorld() && !bot->IsBeingTeleported())
        {
            // If the bot is on the specified dungeon
            Map* map = bot->GetMap();
            if (map && (map->IsDungeon() || map->IsRaid()))
            {
                return map->GetId() == mapID;
            }
        }
    }

    return false;
}

bool LeaveDungeonTrigger::IsActive()
{
    // Don't trigger if strategy already unset
    if (ai->HasStrategy(dungeonStrategy, BotState::BOT_STATE_COMBAT))
    {
        // If the bot is ready
        if (bot->IsInWorld() && !bot->IsBeingTeleported())
        {
            // If the bot is not on the specified dungeon
            return bot->GetMapId() != mapID;
        }
    }

    return false;
}

bool StartBossFightTrigger::IsActive()
{
    // Don't trigger if strategy already set
    if (!ai->HasStrategy(bossStrategy, BotState::BOT_STATE_COMBAT))
    {
        // If the bot is ready
        if (bot->IsInWorld() && !bot->IsBeingTeleported())
        {
            AiObjectContext* context = ai->GetAiObjectContext();
            const std::list<ObjectGuid> attackers = AI_VALUE(std::list<ObjectGuid>, "attackers");
            for (const ObjectGuid& attackerGuid : attackers)
            {
                Unit* attacker = ai->GetUnit(attackerGuid);
                if (attacker && attacker->GetEntry() == bossID)
                {
                    return true;
                }
            }
        }
    }

    return false;
}

bool EndBossFightTrigger::IsActive()
{
    // Don't trigger if strategy already unset
    if (ai->HasStrategy(bossStrategy, BotState::BOT_STATE_COMBAT))
    {
        // We consider the fight is over if not in combat
        return !ai->IsStateActive(BotState::BOT_STATE_COMBAT);
    }

    return false;
}

bool CloseToHazardTrigger::IsActive()
{
    // If the bot is ready
    bool closeToHazard = false;
    if (bot->IsInWorld() && !bot->IsBeingTeleported())
    {
        const std::list<ObjectGuid>& possibleHazards = GetPossibleHazards();
        for (const ObjectGuid& possibleHazardGuid : possibleHazards)
        {
            if (IsHazardValid(possibleHazardGuid))
            {
                // Check if the bot is inside the hazard
                const float distanceToHazard = GetDistanceToHazard(possibleHazardGuid);
                if (distanceToHazard <= hazardRadius)
                {
                    closeToHazard = true;
                }
                Hazard hazard(possibleHazardGuid, hazardDuration, hazardRadius);
                SET_AI_VALUE(Hazard, "add hazard", std::move(hazard));
            }
        }
    }

    // A previous movement action does not prove the bot escaped: it can have
    // failed, stopped, or entered a newly spawned hazard. Recheck actual position.
    return closeToHazard;
}

bool CloseToHazardTrigger::IsHazardValid(const ObjectGuid& hazzardGuid)
{
    if (hazzardGuid.IsGameObject())
    {
        GameObject* hazard = ai->GetGameObject(hazzardGuid);
        return hazard && bot->IsInMap(hazard) && hazard->IsSpawned();
    }
    else if (hazzardGuid.IsCreature())
    {
        Creature* hazard = ai->GetCreature(hazzardGuid);
        return hazard && bot->IsInMap(hazard) && hazard->IsAlive();
    }

    return false;
}

float CloseToHazardTrigger::GetDistanceToHazard(const ObjectGuid& hazzardGuid)
{
    if (hazzardGuid.IsGameObject())
    {
        GameObject* gameObjectHazard = ai->GetGameObject(hazzardGuid);
        if (gameObjectHazard)
        {
            return bot->GetDistance(gameObjectHazard) + gameObjectHazard->GetObjectBoundingRadius();
        }
    }
    else if (hazzardGuid.IsCreature())
    {
        Creature* creatureHazard = ai->GetCreature(hazzardGuid);
        if (creatureHazard)
        {
            return bot->GetDistance(creatureHazard, true, DIST_CALC_COMBAT_REACH);
        }
    }

    return 99999999.0f;
}

std::list<ObjectGuid> CloseToGameObjectHazardTrigger::GetPossibleHazards()
{
    // This game objects have a maximum range equal to the sight distance on config file (default 60 yards)
    return AI_VALUE2(std::list<ObjectGuid>, "nearest game objects no los", gameObjectID);
}

std::list<ObjectGuid> CloseToCreatureHazardTrigger::GetPossibleHazards()
{
    std::list<ObjectGuid> possibleHazards;

    std::list<Unit*> creatures;
    MaNGOS::AllCreaturesOfEntryInRangeCheck u_check(bot, creatureID, hazardRadius);
    MaNGOS::UnitListSearcher<MaNGOS::AllCreaturesOfEntryInRangeCheck> searcher(creatures, u_check);
    Cell::VisitAllObjects(bot, searcher, hazardRadius);
    for (Unit* unit : creatures)
    {
        possibleHazards.push_back(unit->GetObjectGuid());
    }

    return possibleHazards;
}

bool CloseToCreatureHazardTrigger::IsHazardValid(const ObjectGuid& hazzardGuid)
{
    Creature* creatureHazard = ai->GetCreature(hazzardGuid);
    if (creatureHazard && bot->IsInMap(creatureHazard) && creatureHazard->IsAlive())
    {
        // Check if the creature is not targeting the bot
        if (!creatureHazard->GetVictim() || (creatureHazard->GetVictim()->GetObjectGuid() != bot->GetObjectGuid()))
        {
            return true;
        }
    }

    return false;
}

std::list<ObjectGuid> CloseToHostileCreatureHazardTrigger::GetPossibleHazards()
{
    std::list<ObjectGuid> possibleHazards;
    std::list<ObjectGuid> attackers = AI_VALUE(std::list<ObjectGuid>, "attackers");

    for (const ObjectGuid& attackerGuid : attackers)
    {
        Creature* attacker = ai->GetCreature(attackerGuid);
        if (attacker && attacker->GetEntry() == creatureID)
        {
            possibleHazards.push_back(attackerGuid);
        }
    }

    return possibleHazards;
}

bool CloseToCreatureTrigger::IsActive()
{
    // If the bot is ready
    if (bot->IsInWorld() && !bot->IsBeingTeleported())
    {
        AiObjectContext* context = ai->GetAiObjectContext();

        // Iterate through the near creatures
        std::list<Unit*> creatures;
        MaNGOS::AllCreaturesOfEntryInRangeCheck u_check(bot, creatureID, range);
        MaNGOS::UnitListSearcher<MaNGOS::AllCreaturesOfEntryInRangeCheck> searcher(creatures, u_check);
        Cell::VisitAllObjects(bot, searcher, range);
        for (Unit* unit : creatures)
        {
            Creature* creature = (Creature*)unit;
            if (creature && creature->IsAlive())
            {
                // Check if the bot is not being targeted by the creature, unless we don't care
                if ((!creature->GetVictim() || (creature->GetVictim()->GetObjectGuid() != bot->GetObjectGuid())) || ignoreVictim)
                {
                    // See if the creature is within the specified distance
                    if (bot->IsWithinDist(creature, range))
                    {
                        return true;
                    }
                }
            }
        }
    }

    return false;
}

bool CloseToSpecificCreaturesTrigger::IsActive()
{
    // If the bot is ready
    if (bot->IsInWorld() && !bot->IsBeingTeleported())
    {
        AiObjectContext* context = ai->GetAiObjectContext();
        std::set<uint32>&creatureIDList = AI_VALUE(std::set<uint32>&, "avoid creature list");
        // Check if any of the creatures listed is nearby
        for (const uint32 creatureToCheck : creatureIDList)
        {
            // Iterate through the near creatures
            std::list<Unit*> creatures;
            MaNGOS::AllCreaturesOfEntryInRangeCheck u_check(bot, creatureToCheck, range);
            MaNGOS::UnitListSearcher<MaNGOS::AllCreaturesOfEntryInRangeCheck> searcher(creatures, u_check);
            Cell::VisitAllObjects(bot, searcher, range);
            for (Unit* unit : creatures)
            {
                Creature* creature = (Creature*)unit;
                if (creature && creature->IsAlive())
                {
                    // Check if the bot is not being targeted by the creature, unless we don't care
                    if ((!creature->GetVictim() || (creature->GetVictim()->GetObjectGuid() != bot->GetObjectGuid())) || ignoreVictim)
                    {
                        // See if the creature is within the specified distance
                        if (bot->IsWithinDist(creature, range))
                        {
                            return true;
                        }
                    }
                }
            }
        }

    }

    return false;
}

bool ItemReadyTrigger::IsActive()
{
    // Check if the bot has the item or if it has cheats enabled
    if (bot->HasItemCount(itemID, 1) || ai->HasCheat(BotCheatMask::item))
    {
        const ItemPrototype* proto = sObjectMgr.GetItemPrototype(itemID);
        if (proto)
        {
            // Check if the item is in cooldown
            bool inCooldown = false;
            for (uint8 i = 0; i < MAX_ITEM_PROTO_SPELLS; ++i)
            {
                if (proto->Spells[i].SpellTrigger != ITEM_SPELLTRIGGER_ON_USE)
                {
                    continue;
                }

                const uint32 spellID = proto->Spells[i].SpellId;
                if (spellID > 0)
                {
                    if (!sServerFacade.IsSpellReady(bot, spellID) ||
                        !sServerFacade.IsSpellReady(bot, spellID, itemID))
                    {
                        inCooldown = true;
                        break;
                    }
                }
            }

            return !inCooldown;
        }
    }

    return false;
}

bool ItemBuffReadyTrigger::IsActive()
{
    if (!bot->HasAura(buffID))
    {
        return ItemReadyTrigger::IsActive();
    }

    return false;
}
