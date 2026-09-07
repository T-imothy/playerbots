#include "playerbot/playerbot.h"
#include "EncounterItemUse.h"

bool ai::IsNativeEncounterItem(uint32 itemId)
{
    return itemId == 19183 || itemId == 24494 || itemId == 31088 || itemId == 32408;
}

bool ai::UseNativeEncounterItem(Player* bot, Item* item, Unit* unit, GameObject* object)
{
    if (!bot || !item || !bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() ||
        bot->IsBeingTeleported() || bot->IsNonMeleeSpellCasted(false) ||
        item->GetOwnerGuid() != bot->GetObjectGuid() || bot->GetItemByGuid(item->GetObjectGuid()) != item ||
        item->IsInTrade() || bot->CanUseItem(item) != EQUIP_ERR_OK) return false;
    const ItemPrototype* proto = item->GetProto();
    if (!proto || !IsNativeEncounterItem(proto->ItemId)) return false;

    uint32 spellId = 0;
    SpellCastTargets targets;
    switch (proto->ItemId)
    {
        case 19183: case 24494:
            if (object || (unit && unit != bot)) return false;
            spellId = proto->ItemId == 19183 ? 23645 : 32028;
            unit = bot;
            break;
        case 31088:
            if (object)
            {
                if (unit || !object->IsInWorld() || !object->IsSpawned() || !bot->IsInMap(object) ||
                    object->HasFlag(GAMEOBJECT_FLAGS, GO_FLAG_NO_INTERACT | GO_FLAG_IN_USE)) return false;
                spellId = 3366; // Actual opening slot; never cast Throw Key on a generator.
                targets.setGOTarget(object);
            }
            else
            {
                if (!unit || unit == bot || !unit->IsPlayer()) return false;
                spellId = 38134;
            }
            break;
        case 32408:
            if (object || !unit || unit == bot) return false;
            spellId = 39948;
            break;
    }
    if (unit)
    {
        if (!unit->IsInWorld() || !unit->IsAlive() || !bot->IsInMap(unit) ||
            !item->IsTargetValidForItemUse(unit)) return false;
        targets.setUnitTarget(unit);
    }
    for (uint8 slot = 0; slot < MAX_ITEM_PROTO_SPELLS; ++slot)
    {
        if (proto->Spells[slot].SpellId != spellId || proto->Spells[slot].SpellTrigger != ITEM_SPELLTRIGGER_ON_USE)
            continue;
        // The client chooses one on-use slot. Dispatch through the same native
        // path, retaining item charges, lock checks and native cast rejection.
#ifdef MANGOSBOT_ZERO
        bot->CastItemUseSpell(item, targets, slot);
#elif defined(MANGOSBOT_ONE)
        bot->CastItemUseSpell(item, targets, 0, slot);
#else
        bot->CastItemUseSpell(item, targets, 0, 0, spellId);
#endif
        // The native spell may have consumed item synchronously.
        return true;
    }
    return false;
}
