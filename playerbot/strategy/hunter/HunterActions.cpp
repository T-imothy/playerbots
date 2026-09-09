
#include "playerbot/playerbot.h"
#include "playerbot/strategy/actions/GenericActions.h"
#include "HunterActions.h"
#include "playerbot/strategy/actions/MovementActions.h"
#include "playerbot/strategy/generic/CombatStrategy.h"

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
    return CastRangedDebuffSpellAction::isUseful() && !HunterWantsViperSting(ai, GetTarget());
}

bool CastViperStingAction::isUseful()
{
    return CastRangedDebuffSpellAction::isUseful() && HunterWantsViperSting(ai, GetTarget());
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

    return CastSpellAction::isUseful() && MeleeCombatTarget(ai, GetTarget()) && HunterAmmoReady(ai) && ai->HasStrategy("ranged", BotState::BOT_STATE_COMBAT) && AI_VALUE(uint32, "active spell") != AI_VALUE2(uint32, "spell id", getName());
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
    // The shared cast duration already includes native cast time and GCD.
    return CastSpellAction::Execute(event);
}


bool CastArcaneShotAction::isUseful()
{
    if (!CastSpellAction::isUseful() || !MeleeCombatTarget(ai, GetTarget()) || !HunterAmmoReady(ai)) return false;
#ifdef MANGOSBOT_TWO
    // Do not spend Explosive Shot's shared cooldown or Lock and Load charges.
    if (HunterSpell(ai, "explosive shot") &&
        (bot->HasAura(56453) || ai->CanCastSpell("explosive shot", GetTarget(), 0))) return false;
#endif
    return true;
}

bool CastMultiShotAction::isUseful()
{
    if (!CastSpellAction::isUseful() || !MeleeCombatTarget(ai, GetTarget())) return false;
    const SpellEntry* spell = sServerFacade.LookupSpellInfo(HunterSpell(ai, "multi-shot"));
    if (!spell) return false;
    float radius = 0.0f;
    for (unsigned i = 0; i < MAX_EFFECT_INDEX; ++i)
    {
        float minCaster = 0.0f, maxTarget = 0.0f;
        if (spell->EffectChainTarget[i] > 1)
        {
            GetChainJumpRange(spell, SpellEffectIndex(i), minCaster, maxTarget);
            radius = std::max(radius, maxTarget);
        }
    }
    return HunterAreaSafe(ai, GetTarget(), radius);
}

bool CastVolleyAction::isUseful()
{
    if (!CastSpellAction::isUseful() || !MeleeCombatTarget(ai, GetTarget())) return false;
    const SpellEntry* spell = sServerFacade.LookupSpellInfo(HunterSpell(ai, "volley"));
    if (!spell) return false;
    float radius = 0.0f;
    for (unsigned i = 0; i < MAX_EFFECT_INDEX; ++i)
        if (spell->EffectRadiusIndex[i]) radius = std::max(radius, GetSpellRadius(sSpellRadiusStore.LookupEntry(spell->EffectRadiusIndex[i])));
    WorldLocation centre = AI_VALUE(WorldLocation, "aoe position");
    return centre.coord_x != 0 ? HunterAreaSafe(ai, centre.coord_x, centre.coord_y, centre.coord_z, radius) : HunterAreaSafe(ai, GetTarget(), radius);
}

bool TrapOnTargetAction::isUseful()
{
    if (!CastSpellAction::isUseful() || !HunterSpell(ai, trapSpell)) return false;
    Unit* target = GetTrapTargetName() == "cc target" ? AI_VALUE2(Unit*, "cc target", trapSpell) :
        GetTrapTargetName() == "self target" ? bot : AI_VALUE(Unit*, "current target");
    if (!target || !target->IsInWorld() || !target->IsAlive() || !bot->IsInMap(target)) return false;
    // Drop locally. Never run through the fight to plant an offensive trap.
    if (target != bot && (!bot->IsWithinDistInMap(target, 4.0f) || !bot->IsWithinLOSInMap(target))) return false;
    if (target == bot && !AI_VALUE(bool, "has attackers")) return false;
    const bool damage = trapSpell == "immolation trap" || trapSpell == "explosive trap" || trapSpell == "snake trap";
    if (damage && (WaitForAttackStrategy::ShouldWait(ai) || !HunterAreaSafe(ai, bot, 10.0f))) return false;
    if (trapSpell == "immolation trap" && target != bot && !MeleeCombatTarget(ai, target)) return false;
#ifdef MANGOSBOT_TWO
    Unit* enemy = AI_VALUE(Unit*, "current target");
    if (damage && enemy && SafeMeleeTargetCount(ai, 10.0f) < 3 && HunterSpell(ai, "black arrow") &&
        ai->CanCastSpell("black arrow", enemy, 0)) return false;
#endif
    return true;
}

bool CastTrapAction::isUseful()
{
    if (!CastSpellAction::isUseful()) return false;
    if (getThreatType() == ActionThreatType::ACTION_THREAT_NONE) return true;
    return !WaitForAttackStrategy::ShouldWait(ai) && AI_VALUE(bool, "has attackers") && HunterAreaSafe(ai, bot, 10.0f);
}

static void StopHunterControlDamage(PlayerbotAI* ai, Unit* target)
{
    if (!target) return;
    Player* bot = ai->GetBot();
    if (ai->GetAiObjectContext()->GetValue<Unit*>("current target")->Get() == target)
    {
        bot->InterruptSpell(CURRENT_AUTOREPEAT_SPELL);
        bot->AttackStop();
    }
    if (Pet* pet = bot->GetPet())
        if (pet->GetVictim() == target)
        {
            WorldPacket data(CMSG_PET_ACTION);
            data << pet->GetObjectGuid() << uint32((ACT_COMMAND << 24) | COMMAND_FOLLOW) << ObjectGuid();
            bot->GetSession()->HandlePetAction(data);
        }
}

bool CastScatterShotOnClosestAttackerTargetingMeAction::Execute(Event& event)
{
    Unit* target = GetTarget();
    const bool cast = CastRangedDebuffSpellAction::Execute(event);
    if (cast) StopHunterControlDamage(ai, target);
    return cast;
}

bool HunterWyvernStingAction::Execute(Event& event)
{
    Unit* target = GetTarget();
    const bool cast = CastCrowdControlSpellAction::Execute(event);
    if (cast) StopHunterControlDamage(ai, target);
    return cast;
}

bool CastReadinessAction::isUseful()
{
    if (!CastBuffSpellAction::isUseful() || !HunterInShotRange(ai, AI_VALUE(Unit*, "current target"))) return false;
    const uint32 rapid = HunterSpell(ai, "rapid fire");
    return rapid && !bot->IsSpellReady(rapid) && !ai->HasAura("rapid fire", bot);
}

bool HunterDisengageAction::isUseful()
{
    if (!CastSpellAction::isUseful() || !bot->IsInCombat()) return false;
    Unit* enemy = AI_VALUE(Unit*, "closest attacker targeting me");
    if (!MeleeCombatTarget(ai, enemy) || !bot->CanReachWithMeleeAttack(enemy)) return false;
    if (!bot->IsSpellReady(HunterSpell(ai, "disengage"))) return false;
#ifdef MANGOSBOT_TWO
    if (!sPlayerbotAIConfig.useKnockback || !ai->HasPlayerNearby() || bot->IsFalling() || bot->IsInWater() || bot->GetTransport() ||
        ai->HasStrategy("stay", BotState::BOT_STATE_COMBAT) || ai->HasStrategy("guard", BotState::BOT_STATE_COMBAT)) return false;
    const SpellEntry* spell = sServerFacade.LookupSpellInfo(HunterSpell(ai, "disengage"));
    if (!spell) return false;
    float time = 0, distance = 0, height = 0;
    bool good = true;
    std::vector<WorldPosition> path;
    const float angle = bot->GetOrientation() + M_PI_F;
    WorldPosition landing = JumpAction::CalculateJumpParameters(WorldPosition(bot), bot, angle,
        spell->CalculateSimpleValue(EFFECT_INDEX_0) / 10.0f, spell->EffectMiscValue[0] / 10.0f,
        time, distance, height, good, path);
    if (!landing || !good || path.empty() || distance < 3.0f ||
        landing.distance(WorldPosition(enemy)) < std::sqrt(bot->GetDistance(enemy, true, DIST_CALC_NONE)) + 3.0f) return false;
    for (const WorldPosition& point : path)
    {
        if (!HunterAreaSafe(ai, point.getX(), point.getY(), point.getZ(), 5.0f)) return false;
        for (const HazardPosition& hazard : AI_VALUE(std::list<HazardPosition>, "hazards"))
            if (point.distance(hazard.first) < hazard.second + 2.0f) return false;
    }
    return true;
#else
    // Classic/TBC Disengage reduces threat on its enemy target; it is no leap.
    return enemy == GetTarget() && (bot->GetGroup() || (bot->GetPet() && bot->GetPet()->IsAlive()));
#endif
}

#ifdef MANGOSBOT_TWO
static bool HunterNeedsFreedom(Unit* unit)
{
    return unit && unit->IsInWorld() && unit->IsAlive() &&
        (unit->HasAuraType(SPELL_AURA_MOD_ROOT) || unit->HasAuraType(SPELL_AURA_MOD_DECREASE_SPEED));
}

Unit* HunterMastersCallAction::GetTarget()
{
    if (HunterNeedsFreedom(bot)) return bot;
    if (Group* group = bot->GetGroup())
        for (GroupReference* ref = group->GetFirstMember(); ref; ref = ref->next())
            if (Player* member = ref->getSource())
                if (HunterNeedsFreedom(member) && bot->IsInMap(member) && bot->IsWithinDistInMap(member, 30.0f) && bot->IsWithinLOSInMap(member)) return member;
    return nullptr;
}

bool HunterMastersCallAction::isUseful()
{
    Pet* pet = bot->GetPet();
    return pet && pet->IsAlive() && pet->IsInWorld() && bot->IsInMap(pet) &&
        bot->IsInCombat() && CastSpellAction::isUseful();
}

bool HunterFreezingArrowAction::isUseful()
{
    Unit* target = GetTarget();
    return CastSpellAction::isUseful() && target && !target->HasBreakableByDamageCrowdControlAura() &&
        !bot->CanReachWithMeleeAttack(target);
}

bool HunterFreezingArrowAction::isPossible()
{
    Unit* target = GetTarget();
    const uint32 spell = HunterSpell(ai, "freezing arrow");
    return target && spell && ai->CanCastSpell(spell, target->GetPositionX(), target->GetPositionY(), target->GetPositionZ(), 0);
}

bool HunterFreezingArrowAction::Execute(Event& event)
{
    if (!isUseful() || !isPossible()) return false;
    Unit* target = GetTarget();
    uint32 duration = 0;
    // Explicit coordinates prevent the generic AoE cluster from replacing the CC target.
    const bool cast = ai->CastSpell(HunterSpell(ai, "freezing arrow"), target->GetPositionX(), target->GetPositionY(), target->GetPositionZ(), nullptr, false, &duration);
    if (cast) { SetDuration(duration); StopHunterControlDamage(ai, target); }
    return cast;
}
#endif
