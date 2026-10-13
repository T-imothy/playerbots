
#include "playerbot/playerbot.h"
#include "RepairAllAction.h"

#include "playerbot/ServerFacade.h"

using namespace ai;

bool RepairAllAction::Execute(Event& event)
{
    Player* requester = event.getOwner() ? event.getOwner() : GetMaster();
    std::list<ObjectGuid> npcs = AI_VALUE(std::list<ObjectGuid>, "nearest npcs");
    for (std::list<ObjectGuid>::iterator i = npcs.begin(); i != npcs.end(); i++)
    {
        Creature *unit = bot->GetNPCIfCanInteractWith(*i, UNIT_NPC_FLAG_REPAIR);
        if (!unit)
            continue;

#ifdef MANGOS
        if(bot->hasUnitState(UNIT_STAT_DIED))
#endif
#ifdef CMANGOS
        if (bot->hasUnitState(UNIT_STAT_FEIGN_DEATH))
#endif
            bot->RemoveSpellsCausingAura(SPELL_AURA_FEIGN_DEATH);

        sServerFacade.SetFacingTo(bot, unit);
        float discountMod = bot->GetReputationPriceDiscount(unit);

        float durability = AI_VALUE(uint8, "durability inventory");

        uint32 botMoney = bot->GetMoney();
        if (ai->HasCheat(BotCheatMask::gold))
        {
            bot->SetMoney(10000000);
        }

        //Repair weapons first.
        uint32 totalCost = bot->DurabilityRepair((INVENTORY_SLOT_BAG_0 << 8) | EQUIPMENT_SLOT_MAINHAND, true, discountMod
#ifndef MANGOSBOT_ZERO
            , false
#endif
        );

        totalCost += bot->DurabilityRepair((INVENTORY_SLOT_BAG_0 << 8) | EQUIPMENT_SLOT_RANGED, true, discountMod
#ifndef MANGOSBOT_ZERO
            , false
#endif
        );

        totalCost += bot->DurabilityRepair((INVENTORY_SLOT_BAG_0 << 8) | EQUIPMENT_SLOT_OFFHAND, true, discountMod
#ifndef MANGOSBOT_ZERO
            , false
#endif
        );

        totalCost += bot->DurabilityRepairAll(true, discountMod
#ifndef MANGOSBOT_ZERO
            , false
#endif
        );

        if (ai->HasCheat(BotCheatMask::gold))
        {
            bot->SetMoney(botMoney);
        }

        //Totalcost is bugged in core. For now we use this work-around.
        totalCost = botMoney - bot->GetMoney();

        if (totalCost > 0)
        {
            std::ostringstream out;
            out << "Repair: " << chat->formatMoney(totalCost) << " (" << unit->GetName() << ")";
            ai->TellPlayerNoFacing(requester, out.str(),PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL, false);
            if (sPlayerbotAIConfig.globalSoundEffects)      
                bot->PlayDistanceSound(7994);

            sPlayerbotAIConfig.logEvent(ai, "RepairAllAction", std::to_string(durability), std::to_string(totalCost));

            ai->DoSpecificAction("equip upgrades", event, true);
        }

        SET_AI_VALUE(uint32, "death count", 0);
        RESET_AI_VALUE(uint8, "durability inventory");

        return durability < 100 && AI_VALUE(uint8, "durability inventory") > durability;
    }

    ai->TellPlayerNoFacing(requester, "Cannot find any npc to repair at");
    return false;
}

Creature* RaidRepairAction::GetRepairNpc()
{
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
        bot->IsInCombat() || ai->IsRealPlayer() || !ai->HasRealPlayerMaster() ||
        !bot->GetGroup() || !bot->GetGroup()->IsRaidGroup() || !bot->GetMoney()) return nullptr;
    for (GroupReference* ref=bot->GetGroup()->GetFirstMember();ref;ref=ref->next())
        if (Player* member=ref->getSource())
            if (member->IsInWorld() && bot->IsInMap(member) && member->IsInCombat()) return nullptr;
    bool damaged=false;
    for (uint8 slot=EQUIPMENT_SLOT_START;slot<EQUIPMENT_SLOT_END;++slot)
        if (Item* item=bot->GetItemByPos(INVENTORY_SLOT_BAG_0,slot))
            if (item->GetUInt32Value(ITEM_FIELD_MAXDURABILITY) &&
                item->GetUInt32Value(ITEM_FIELD_DURABILITY)<item->GetUInt32Value(ITEM_FIELD_MAXDURABILITY)) damaged=true;
    if (!damaged) return nullptr;
    Creature* best=nullptr;
    for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("nearest npcs")->Get())
    {
        Unit* unit=ai->GetUnit(guid);
        if (!unit || unit->GetTypeId()!=TYPEID_UNIT || !unit->IsInWorld() || !unit->IsAlive() ||
            !bot->IsInMap(unit) || unit->HasCharmer() || !unit->HasFlag(UNIT_NPC_FLAGS,UNIT_NPC_FLAG_REPAIR) ||
            !sServerFacade.IsFriendlyTo(bot,unit) || bot->GetDistance(unit)>30) continue;
        Creature* npc=static_cast<Creature*>(unit);
        if (!best || bot->GetDistance(npc)<bot->GetDistance(best)) best=npc;
    }
    return best;
}

bool RaidRepairAction::isUseful()
{
    return MovementAction::isUseful() && GetRepairNpc();
}

bool RaidRepairAction::Execute(Event& event)
{
    Creature* npc=GetRepairNpc();
    if (!npc || !ai->CanMove()) return false;
    if (!bot->GetNPCIfCanInteractWith(npc->GetObjectGuid(),UNIT_NPC_FLAG_REPAIR))
        return MoveNear(npc,INTERACTION_DISTANCE-1.0f);
    // Existing native repair action pays normal costs; no item, gold,
    // durability, cooldown or in-combat repair shortcut is introduced.
    RepairAllAction repair(ai);
    const bool repaired=repair.Execute(event);
    SetDuration(sPlayerbotAIConfig.reactDelay);
    return repaired;
}
