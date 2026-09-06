
#include "playerbot/playerbot.h"
#include "playerbot/strategy/actions/GenericActions.h"
#include "HunterActions.h"

using namespace ai;

bool CastExplosiveShotAction::isUseful()
{
#ifdef MANGOSBOT_TWO
    if (!CastSpellAction::isUseful()) return false;
    // Lock and Load can make another shot ready before the final periodic tick.
    // Do not overwrite our own running effect; another hunter's effect is not ours.
    Aura* aura = ai->GetAura("explosive shot", GetTarget(), true);
    return !aura || !aura->GetHolder() || aura->GetHolder()->GetAuraDuration() <= 0;
#else
    return false;
#endif
}

bool CastSerpentStingAction::isUseful()
{
    return CastRangedDebuffSpellAction::isUseful() && AI_VALUE2(uint8, "health", GetTargetName()) > 50 &&
        (!AI_VALUE2(bool, "has mana", GetTargetName()) || AI_VALUE2(uint8, "mana", GetTargetName()) < 10 ||
            ai->HasStrategy("sting serpent", BotState::BOT_STATE_COMBAT));
}

bool CastViperStingAction::isUseful()
{
    return CastRangedDebuffSpellAction::isUseful() && AI_VALUE2(bool, "has mana", GetTargetName()) &&
        AI_VALUE2(uint8, "mana", GetTargetName()) >= 10;
}

bool FeedPetAction::Execute(Event& event)
{
    Pet* pet = bot->GetPet();
    if (pet && pet->getPetType() == HUNTER_PET && pet->GetHappinessState() != HAPPY)
        pet->SetPower(POWER_HAPPINESS, HAPPINESS_LEVEL_SIZE * 2);

    return true;
}

bool CastAutoShotAction::isUseful()
{
    if (ai->IsInVehicle() && !ai->IsInVehicle(false, false, true))
        return false;

    return ai->HasStrategy("ranged", BotState::BOT_STATE_COMBAT) && AI_VALUE(uint32, "active spell") != AI_VALUE2(uint32, "spell id", getName());
}

bool HunterEquipAmmoAction::Execute(Event& event)
{
    // Get ranged weapon
    Item* ranged = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, EQUIPMENT_SLOT_RANGED);
    if (!ranged)
        return false;

    uint32 subClass = 0;

    switch (ranged->GetProto()->SubClass)
    {
    case ITEM_SUBCLASS_WEAPON_GUN:
        subClass = ITEM_SUBCLASS_BULLET;
        break;
    case ITEM_SUBCLASS_WEAPON_BOW:
    case ITEM_SUBCLASS_WEAPON_CROSSBOW:
        subClass = ITEM_SUBCLASS_ARROW;
        break;
    default:
        // Thrown weapons/wands do not use the projectile ammo slot.
        return false;
    }

    uint32 currentAmmoId = bot->GetUInt32Value(PLAYER_AMMO_ID);
    const ItemPrototype* bestAmmoProto = nullptr;

    auto considerAmmo = [&](Item* item)
    {
        if (!item)
            return;
        const ItemPrototype* proto = item->GetProto();
        if (!proto || proto->Class != ITEM_CLASS_PROJECTILE || proto->SubClass != subClass ||
            bot->CanUseAmmo(proto->ItemId) != EQUIP_ERR_OK)
            return;
        if (!bestAmmoProto || proto->ItemLevel > bestAmmoProto->ItemLevel)
            bestAmmoProto = proto;
    };

    // Backpack plus equipped bags, never bank contents.
    for (uint8 slot = INVENTORY_SLOT_ITEM_START; slot < INVENTORY_SLOT_ITEM_END; ++slot)
        considerAmmo(bot->GetItemByPos(INVENTORY_SLOT_BAG_0, slot));

    for (int i = INVENTORY_SLOT_BAG_START; i < INVENTORY_SLOT_BAG_END; ++i)
    {
        if (Bag* bag = (Bag*)bot->GetItemByPos(INVENTORY_SLOT_BAG_0, i))
        {
            for (uint32 j = 0; j < bag->GetBagSize(); ++j)
            {
                considerAmmo(bag->GetItemByPos(j));
            }
        }
    }

    // Equip best ammo if not already equipped
    if (bestAmmoProto && currentAmmoId != bestAmmoProto->ItemId)
    {
        bot->SetAmmo(bestAmmoProto->ItemId);
        return bot->GetUInt32Value(PLAYER_AMMO_ID) == bestAmmoProto->ItemId;
    }

    return false;
}

bool CastAutoShotAction::Execute(Event& event)
{
    if (!bot->IsStopped())
    {
        ai->StopMoving();
    }

    return CastSpellAction::Execute(event);
}

bool CastSteadyShotAction::Execute(Event& event)
{
    if (CastSpellAction::Execute(event))
    {
        const Item* equippedWeapon = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, EQUIPMENT_SLOT_RANGED);
        if (equippedWeapon)
        {
            SetDuration(GetDuration() + sPlayerbotAIConfig.globalCoolDown);
        }

        return true;
    }

    return false;
}
