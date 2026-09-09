
#include "playerbot/playerbot.h"
#include "GenericActions.h"
#include "UseItemAction.h"
#include "playerbot/CombatDiagnostics.h"
#include "EncounterSpellPolicy.h"
#include "playerbot/strategy/Trigger.h"
#include "playerbot/strategy/warrior/WarriorCombatPolicy.h"

using namespace ai;

CastSpellAction::CastSpellAction(PlayerbotAI* ai, std::string spell)
: Action(ai, spell)
, range(ai->GetRange("spell"))
{
    SetSpellName(spell);

    float spellRange;
    if (ai->GetSpellRange(spell, &spellRange))
    {
        range = spellRange;
    }
}

bool CastSpellAction::HasMovementEffect()
{
    RefreshSpellId();
    const SpellEntry* spell = sServerFacade.LookupSpellInfo(spellId);
    if (!spell) return false;
    for (unsigned effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
        switch (spell->Effect[effect])
        {
            case SPELL_EFFECT_CHARGE:
            case SPELL_EFFECT_LEAP:
            case SPELL_EFFECT_TELEPORT_UNITS:
            case SPELL_EFFECT_TELEPORT_UNITS_FACE_CASTER:
#ifndef MANGOSBOT_ZERO
            case SPELL_EFFECT_LEAP_BACK:
            case SPELL_EFFECT_CHARGE_DEST:
#endif
#ifdef MANGOSBOT_TWO
            case SPELL_EFFECT_JUMP:
            case SPELL_EFFECT_JUMP_DEST:
#endif
                return true;
            default: break;
        }
    return false;
}

bool CastSpellAction::Execute(Event& event)
{
    RefreshSpellId();
    bool executed = false;
    uint32 observedSpellId = spellId;
    uint32 spellDuration = sPlayerbotAIConfig.globalCoolDown;
    if (spellName == "conjure food" || spellName == "conjure water")
    {
        uint32 castId = 0;
        for (PlayerSpellMap::iterator itr = bot->GetSpellMap().begin(); itr != bot->GetSpellMap().end(); ++itr)
        {
            uint32 spellId = itr->first;

            // Removed/disabled ranks remain in the spell map until save. Use
            // the native learned-spell predicate before selecting a conjure rank.
            if (!bot->HasSpell(spellId))
                continue;

            const SpellEntry* pSpellInfo = sServerFacade.LookupSpellInfo(spellId);
            if (!pSpellInfo || IsPassiveSpell(pSpellInfo))
                continue;

            std::string namepart = pSpellInfo->SpellName[0];
            strToLower(namepart);

            if (namepart.find(spellName) == std::string::npos)
                continue;

            if (pSpellInfo->Effect[0] != SPELL_EFFECT_CREATE_ITEM)
                continue;

            uint32 itemId = pSpellInfo->EffectItemType[0];
            ItemPrototype const* proto = sObjectMgr.GetItemPrototype(itemId);
            if (!proto)
                continue;

            if (bot->CanUseItem(proto) != EQUIP_ERR_OK)
                continue;

            if (pSpellInfo->Id > castId)
                castId = pSpellInfo->Id;
        }

        if (!castId || !sServerFacade.LookupSpellInfo(castId))
            return false;

        executed = ai->CastSpell(castId, bot, nullptr, false, &spellDuration);
        observedSpellId = castId;
    }
    else
    {
        // Keep invalid and expansion-incompatible actions out of the core spell
        // path. Dynamic mount selection is still resolved by the normal value.
        if (!spellId || !sServerFacade.LookupSpellInfo(spellId))
            return false;
        if (IsPassiveSpell(sServerFacade.LookupSpellInfo(spellId)))
            return false;

        // The native class-call aura can arrive after action selection.
        if (ShouldAvoidCorruptedHealing(bot, sServerFacade.LookupSpellInfo(spellId), GetTarget()))
            return false;
        if (ShouldAvoidEncounterDispel(ai, sServerFacade.LookupSpellInfo(spellId), GetTarget()))
            return false;
        if (ShouldAvoidEncounterTaunt(ai, sServerFacade.LookupSpellInfo(spellId), GetTarget()))
            return false;
        if (ShouldAvoidEncounterOffense(bot, bot, sServerFacade.LookupSpellInfo(spellId), GetTarget()))
            return false;

        if (GetTargetName() == "current target" && (!bot->GetCurrentSpell(CURRENT_MELEE_SPELL) && !bot->GetCurrentSpell(CURRENT_AUTOREPEAT_SPELL)))
        {
            if (bot->getClass() == CLASS_HUNTER && spellName != "auto shot" && sServerFacade.GetDistance2d(bot, GetTarget()) > 5.0f)
                ai->CastSpell("auto shot", GetTarget());
        }

        executed = ai->CastSpell(spellName, GetTarget(), nullptr, false, &spellDuration);
    }

    if (CombatDiagnostics::Select(ai))
        CombatDiagnostics::Record(ai, getName(), event.getSource(), "cast_wrapper_result", executed ? 1 : 0, observedSpellId);

    if (executed)
    {
        if (ai->HasCheat(BotCheatMask::attackspeed))
            spellDuration = 1;

        SetDuration(spellDuration);
    }

    return executed;
}

Unit* TankThreatTransferAction::GetTarget()
{
    if (!bot->GetGroup()) return nullptr;
    Unit* enemy = context->GetValue<Unit*>("current target")->Get();
    Unit* tank = enemy && enemy->IsInWorld() && enemy->GetMap() == bot->GetMap() ? enemy->GetVictim() : nullptr;
    if (tank && tank->IsPlayer() && tank != bot && tank->IsAlive() && tank->IsInWorld() &&
        tank->GetMap() == bot->GetMap() && static_cast<Player*>(tank)->GetGroup() == bot->GetGroup() && ai->IsTank(static_cast<Player*>(tank)))
        return tank;
    return BuffOnTankAction::GetTarget();
}

bool TankThreatTransferAction::isUseful()
{
    // Keep manual cast commands separate. Automatic threat support belongs on
    // a living group tank, not an arbitrary healer or the transferring bot.
    if (!bot->IsInWorld() || !bot->GetGroup() || bot->HasCharmer() || ai->IsTank(bot) ||
        ai->HasAura(GetSpellName(), bot)) return false;
    Unit* target = GetTarget();
    if (!target || target == bot || !target->IsPlayer() || !target->IsInWorld() ||
        !target->IsAlive() || target->HasCharmer() || target->GetMap() != bot->GetMap() ||
        static_cast<Player*>(target)->GetGroup() != bot->GetGroup() || !ai->IsTank(static_cast<Player*>(target))) return false;
    return CastSpellAction::isUseful();
}

bool CastSpellAction::isPossible()
{
    RefreshSpellId();
    if (!spellId || !sServerFacade.LookupSpellInfo(spellId))
        return false;
    if (IsPassiveSpell(sServerFacade.LookupSpellInfo(spellId)))
        return false;

    if (spellName == "mount")
    {
        if (!bot->IsMounted() && !bot->IsInCombat())
        {
            return true;
        }
        if (bot->IsInCombat())
        {
            ai->Unmount();
            return false;
        }
    }

    Unit* spellTarget = GetTarget();
    if (!spellTarget)
        return false;

    // Native hunter ranged checks include this target's reach and the
    // expansion's minimum range. Do not reject them with a caster-only estimate.
    const SpellEntry* nativeSpell = sServerFacade.LookupSpellInfo(spellId);
    if (bot->getClass() == CLASS_HUNTER && nativeSpell->HasAttribute(SPELL_ATTR_USES_RANGED_SLOT))
        return ai->CanCastSpell(spellName, spellTarget, 0);

    bool canReach = false;
    if (spellTarget == bot)
    {
        canReach = true;
    }
    else
    {
        float dist = bot->GetDistance(spellTarget, true, ai->IsRanged(bot) ? DIST_CALC_COMBAT_REACH : DIST_CALC_COMBAT_REACH_WITH_MELEE);
        if (range == ATTACK_DISTANCE) 
        {
            canReach = bot->CanReachWithMeleeAttack(spellTarget);
        }
        else 
        {
            canReach = dist <= (range + sPlayerbotAIConfig.contactDistance);
            if (!spellId)
                return false;

            const SpellEntry* pSpellInfo = sServerFacade.LookupSpellInfo(spellId);
            if (!pSpellInfo)
                return false;

            if (range != ATTACK_DISTANCE && pSpellInfo->rangeIndex != SPELL_RANGE_IDX_COMBAT && pSpellInfo->rangeIndex != SPELL_RANGE_IDX_SELF_ONLY && pSpellInfo->rangeIndex != SPELL_RANGE_IDX_ANYWHERE)
            {
                float max_range, min_range;
                if (ai->GetSpellRange(GetSpellName(), &max_range, &min_range))
                {
                    canReach = dist < max_range && dist >= min_range;
                }
            }
        }
    }

    if(!canReach)
    {
        return false;
    }
    
    // Check if the spell can be casted
	return ai->CanCastSpell(spellName, spellTarget, 0, nullptr, true);
}

bool CastSpellAction::ShouldTryAlternativesWhenUseless()
{
    // Vehicle abilities have their own capability checks and spellbook.
    if (spellIdContext != "spell id")
        return false;
    RefreshSpellId();
    const SpellEntry* spell = sServerFacade.LookupSpellInfo(spellId);
    return !spellId || !spell || !ai->HasSpell(spellId) || IsPassiveSpell(spell);
}

bool CastSpellAction::isUseful()
{
    RefreshSpellId();
    // Expansion-specific strategies can expose actions for spells this bot has
    // not learned (or that do not exist in the current client data). Reject
    // those static capability misses before target/range/cast evaluation. The
    // cached HasSpell path is invalidated by spellbook/talent changes.
    if (!spellId || !sServerFacade.LookupSpellInfo(spellId) || !ai->HasSpell(spellId))
        return false;
    // A learned talent/proc can appear in the spellbook without being an
    // activated ability. Its effects are applied by the core, not recast by AI.
    if (IsPassiveSpell(sServerFacade.LookupSpellInfo(spellId)))
        return false;

    if (ai->IsInVehicle() && !ai->IsInVehicle(false, false, true))
        return false;

    if(!AI_VALUE2(bool, "spell cast useful", spellName))
        return false;

    Unit* spellTarget = GetTarget();
    if (!spellTarget)
        return false;

    if (!bot->IsInWorld() || bot->IsBeingTeleported() || !spellTarget->IsInWorld() || !bot->IsInMap(spellTarget))
        return false;

    if (bot->getClass() == CLASS_HUNTER && spellTarget != bot &&
        getThreatType() != ActionThreatType::ACTION_THREAT_NONE &&
        spellTarget->HasBreakableByDamageCrowdControlAura() && bot->CanAttack(spellTarget)) return false;

    const SpellEntry* pSpellInfo = sServerFacade.LookupSpellInfo(spellId);
    if (ShouldAvoidCorruptedHealing(bot, pSpellInfo, spellTarget))
        return false;
    if (ShouldAvoidEncounterDispel(ai, pSpellInfo, spellTarget))
        return false;
    if (ShouldAvoidEncounterTaunt(ai, pSpellInfo, spellTarget))
        return false;
    if (ShouldAvoidEncounterOffense(bot, bot, pSpellInfo, spellTarget))
        return false;
    if (pSpellInfo)
    {
        // check if the damage we'd take from damage shields is too harmful, only for melee spells
        if (range == ATTACK_DISTANCE)
        {
            std::set<Aura*> alreadyDone;
            Unit::AuraList const& vDamageShields = spellTarget->GetAurasByType(SPELL_AURA_DAMAGE_SHIELD);
            for (Unit::AuraList::const_iterator i = vDamageShields.begin(); i != vDamageShields.end();)
            {
                if (alreadyDone.find(*i) == alreadyDone.end())
                {
                    alreadyDone.insert(*i);
                    uint32 damage = (*i)->GetModifier()->m_amount;

                    // If the damage shield does at least 10% of our max hp on each hit we do, we shouldn't cast a melee spell
                    if (damage >= bot->GetMaxHealth() * 0.10f)
                    {
                        bot->AttackStop();
                        return false;
                    }

                    i = vDamageShields.begin();
                }
                else
                    ++i;
            }
        }

        // At even odds or worse, do not cast a reflectable spell. Use the
        // native school-specific chance and reflectability, not a boss ID.
        if (spellTarget->GetReflectChance(GetSpellSchoolMask(pSpellInfo)) >= 50.0f && IsReflectableSpell(pSpellInfo))
            return false;
    }

    return true;
}

NextAction** CastSpellAction::getPrerequisites()
{
    NextAction** prerequisites = Action::getPrerequisites();
    const std::string stance = WarriorStancePrerequisite(ai, sServerFacade.LookupSpellInfo(spellId));
    if (!stance.empty() && CanPlanWarriorSpell(ai, spellName, GetTarget()))
        prerequisites = NextAction::merge(NextAction::array(0, new NextAction(stance), nullptr), prerequisites);
    // Set the reach action as the cast spell prerequisite when needed
    const std::string reachAction = GetReachActionName();
    if (!reachAction.empty())
    {
        const std::string targetName = GetTargetName();

        // No need for a reach action when target is self
        if (targetName != "self target")
        {
            const std::string spellName = GetSpellName();
            const std::string targetQualifier = GetTargetQualifier();

            // Generate the reach action with qualifiers
            std::vector<std::string> qualifiers = { spellName, targetName };
            if (!targetQualifier.empty())
            {
                qualifiers.push_back(targetQualifier);
            }

            const std::string qualifiersStr = Qualified::MultiQualify(qualifiers, "::");
            return NextAction::merge(NextAction::array(0, new NextAction(reachAction + "::" + qualifiersStr), NULL), prerequisites);
        }
    }

    return prerequisites;
}

void CastSpellAction::SetSpellName(const std::string& name, std::string spellIDContextName /*= "spell id"*/, bool force)
{
    if (force || spellName != name || spellIdContext != spellIDContextName)
    {
        spellName = name;
        spellIdContext = spellIDContextName;
        spellId = ai->GetAiObjectContext()->GetValue<uint32>(spellIDContextName, name)->Get();

        float spellRange;
        if (ai->GetSpellRange(spellName, &spellRange))
        {
            range = spellRange;
        }
    }
}

void CastSpellAction::RefreshSpellId()
{
    // Reuse the existing timed spell-ID value. An Action outlives training,
    // respecs and pet changes; its constructor's ID is not a permanent capability.
    spellId = ai->GetAiObjectContext()->GetValue<uint32>(spellIdContext, spellName)->Get();
}

Unit* CastSpellAction::GetTarget()
{
    std::string targetName = GetTargetName();
    std::string targetNameQualifier = GetTargetQualifier();
    return targetNameQualifier.empty() ? AI_VALUE(Unit*, targetName) : AI_VALUE2(Unit*, targetName, targetNameQualifier);
}

bool CastPetSpellAction::isPossible()
{
    RefreshSpellId();
    Unit* spellTarget = GetTarget();
    if (!spellTarget)
        return false;

    Unit* pet = AI_VALUE(Unit*, "pet target");
    if (pet && ai->IsSafe(pet))
    {
        const uint32& spellId = GetSpellID();
        if (pet->HasSpell(spellId) && pet->IsSpellReady(spellId))
        {
            // Check if the pet is not too far from the owner
            if (bot->GetDistance(pet) <= sPlayerbotAIConfig.sightDistance)
            {
                bool canReach = false;
                const SpellEntry* pSpellInfo = sServerFacade.LookupSpellInfo(spellId);
                if (pSpellInfo)
                {
                    const float dist = pet->GetDistance(spellTarget, true, DIST_CALC_COMBAT_REACH);
                    canReach = dist <= (range + sPlayerbotAIConfig.contactDistance);

                    if (pSpellInfo->rangeIndex != SPELL_RANGE_IDX_COMBAT && pSpellInfo->rangeIndex != SPELL_RANGE_IDX_SELF_ONLY && pSpellInfo->rangeIndex != SPELL_RANGE_IDX_ANYWHERE)
                    {
                        float max_range, min_range;
                        if (ai->GetSpellRange(GetSpellName(), &max_range, &min_range))
                        {
                            canReach = dist < max_range&& dist >= min_range;
                        }
                    }
                }

                if (canReach)
                {
                    return ai->CanCastSpell(spellId, spellTarget, 0, true);
                }
            }
        }
    }

    return false;
}

bool CastAuraSpellAction::isUseful()
{
    return CastSpellAction::isUseful() && !ai->HasAura(GetSpellName(), GetTarget(), false, isOwner);
}

bool CastMeleeAoeSpellAction::isUseful()
{
    return CastSpellAction::isUseful() && sServerFacade.IsDistanceLessOrEqualThan(AI_VALUE2(float, "distance", GetTargetName()), radius);
}

bool CastEnchantItemAction::isPossible()
{
    if (!CastSpellAction::isPossible())
        return false;

    return GetSpellID() && AI_VALUE2(Item*, "item for spell", GetSpellID());
}

bool CastAoeHealSpellAction::isUseful()
{
    RefreshSpellId();
    Unit* target = GetTarget();
    if (target && target->GetMaxNegativeAuraModifier(SPELL_AURA_MOD_HEALING_PCT) <= -100 &&
        !CanPrecastEncounterHeal(bot, target, sServerFacade.LookupSpellInfo(GetSpellID()))) return false;
    return CastSpellAction::isUseful();
}

bool HealHotPartyMemberAction::isUseful()
{
    return HealPartyMemberAction::isUseful() && !ai->HasAura(GetSpellName(), GetTarget());
}

bool CastVehicleSpellAction::isPossible()
{
    RefreshSpellId();
    return ai->CanCastVehicleSpell(GetSpellID(), GetTarget());
}

bool CastVehicleSpellAction::isUseful()
{
    RefreshSpellId();
    return ai->IsInVehicle(false, true);
}

bool CastVehicleSpellAction::Execute(Event& event)
{
    RefreshSpellId();
    return ai->CastVehicleSpell(GetSpellID(), GetTarget(), speed, needTurn);
}

bool CastFrozenDeathboltAction::isPossible()
{
    Unit* target = GetTarget();

    if (!target)
        return false;

    if (target->GetDistance(bot) > range)
        return false;

    return CastVehicleSpellAction::isPossible();
}

bool CastWarStompAction::isUseful()
{
    // ignore distance check in pvp or duel
    if (!ai->HasStrategy("pvp", BotState::BOT_STATE_COMBAT) &&
        !ai->HasStrategy("duel", BotState::BOT_STATE_COMBAT))
    {
        Unit* target = AI_VALUE(Unit*, "current target");
        if (target)
            return AI_VALUE2(float, "distance", "current target") <= 8.0f;
        return false;
    }

    return true;
}

bool CastDevourHumanoidAction::isPossible()
{
    Unit* target = GetTarget();

    if (!target)
        return false;

    if (target->GetDistance(bot) > range)
        return false;

    return CastVehicleSpellAction::isPossible();
}

bool CastShootAction::isUseful()
{
    // The engine checks usefulness before possibility. Resolve the equipped
    // weapon here so Classic's Shoot Bow/Gun/Crossbow and Throw reach the
    // learned-spell check instead of being rejected as generic Shoot.
    UpdateWeaponInfo();
    return rangedWeapon && !needsAmmo && CastSpellAction::isUseful();
}

bool CastShootAction::isPossible()
{
    // Check if the bot has a ranged weapon equipped and has ammo
    UpdateWeaponInfo();
    if (rangedWeapon && !needsAmmo)
    {
        // Check if the target exist and it can be shot
        Unit* target = GetTarget();
        if (target && sServerFacade.IsWithinLOSInMap(bot, target))
        {
            return CastSpellAction::isPossible();
        }
    }

    return false;
}

bool CastShootAction::Execute(Event& event)
{
    bool succeeded = false;

    UpdateWeaponInfo();
    if (rangedWeapon && !needsAmmo)
    {
        // Prevent calling the shoot spell when already active
        Spell* autoRepeatSpell = ai->GetBot()->GetCurrentSpell(CURRENT_AUTOREPEAT_SPELL);
        if (autoRepeatSpell && (autoRepeatSpell->m_spellInfo->Id == GetSpellID()))
        {
            succeeded = true;
        }
        else if (CastSpellAction::Execute(event))
        {
            succeeded = true;
        }

        if (succeeded)
        {
            SetDuration(weaponDelay);
        }
    }

    return succeeded;
}

void CastShootAction::UpdateWeaponInfo()
{
    // Check if we have a new ranged weapon equipped
    const Item* equippedWeapon = bot->GetItemByPos(INVENTORY_SLOT_BAG_0, EQUIPMENT_SLOT_RANGED);
    if (equippedWeapon)
    {
        if (equippedWeapon != rangedWeapon)
        {
            std::string spellName = "shoot";
            bool isRangedWeapon = false;

#ifdef MANGOSBOT_ZERO
            needsAmmo = true;
#endif

            const ItemPrototype* itemPrototype = equippedWeapon->GetProto();
            switch (itemPrototype->SubClass)
            {
                case ITEM_SUBCLASS_WEAPON_GUN:
                {
                    isRangedWeapon = true;
#ifdef MANGOSBOT_ZERO
                    spellName += " gun";
#endif
                    break;
                }
                case ITEM_SUBCLASS_WEAPON_BOW:
                {
                    isRangedWeapon = true;
#ifdef MANGOSBOT_ZERO
                    spellName += " bow";
#endif
                    break;
                }
                case ITEM_SUBCLASS_WEAPON_CROSSBOW:
                {
                    isRangedWeapon = true;
#ifdef MANGOSBOT_ZERO
                    spellName += " crossbow";
#endif
                    break;
                }
                case ITEM_SUBCLASS_WEAPON_WAND:
                {
                    isRangedWeapon = true;
#ifdef MANGOSBOT_ZERO
                    needsAmmo = false;
#endif
                    break;
                }
                case ITEM_SUBCLASS_WEAPON_THROWN:
                {
                    isRangedWeapon = true;
                    spellName = "throw";
                    break;
                }

                default: break;
            }

            // Set the new weapon parameters
            if (isRangedWeapon)
            {
                SetSpellName(spellName);
                rangedWeapon = equippedWeapon;
                weaponDelay = itemPrototype->Delay + sPlayerbotAIConfig.globalCoolDown;
            }
        }

        // Check the ammunition
#ifdef MANGOSBOT_ZERO
        needsAmmo = (GetSpellName() != "shoot") ? (AI_VALUE2(uint32, "item count", "ammo") <= 0) : false;
#endif
    }
    else
    {
        rangedWeapon = nullptr;
    }
}

bool RemoveBuffAction::isUseful()
{
    return ai->HasAura(name, bot);
}

bool RemoveBuffAction::Execute(Event& event)
{
    ai->RemoveAura(name);
    return !ai->HasAura(name, bot);
}

bool InterruptCurrentSpellAction::isUseful()
{
    for (int type = CURRENT_MELEE_SPELL; type < CURRENT_CHANNELED_SPELL; type++)
    {
        Spell* currentSpell = bot->GetCurrentSpell((CurrentSpellTypes)type);
        if (currentSpell && currentSpell->CanBeInterrupted())
            return true;
    }
    return false;
}

bool InterruptCurrentSpellAction::Execute(Event& event)
{
    const bool cancelOverheal = event.getSource() == "heal target full health";
    if (cancelOverheal)
    {
        // An action can wait in the queue while health or the active cast changes.
        Trigger* trigger = ai->GetAiObjectContext()->GetTrigger("heal target full health");
        if (!trigger || !trigger->IsActive())
            return false;
    }
    bool interrupted = false;
    for (int type = CURRENT_MELEE_SPELL; type < CURRENT_CHANNELED_SPELL; type++)
    {
        if (cancelOverheal && type != CURRENT_GENERIC_SPELL)
            continue;
        Spell* currentSpell = bot->GetCurrentSpell((CurrentSpellTypes)type);
        if (currentSpell && currentSpell->CanBeInterrupted())
        {
            const uint32 spellId = currentSpell->m_spellInfo->Id;
            bot->InterruptSpell((CurrentSpellTypes)type);
            ai->SpellInterrupted(spellId);
            interrupted = true;
        }
    }
    return interrupted;
}

Unit* CastSpellTargetAction::GetTarget()
{
    // Check for assigned targets
    const std::list<ObjectGuid>& possibleTargets = AI_VALUE(std::list<ObjectGuid>, targetsValue);
    if (!possibleTargets.empty())
    {
        for (const ObjectGuid& possibleTargetGuid : possibleTargets)
        {
            Unit* possibleTarget = ai->GetUnit(possibleTargetGuid);
            if (IsTargetValid(possibleTarget))
            {
                return possibleTarget;
            }
        }
    }
    else
    {
        // Check for the default target
        Unit* possibleTarget = CastSpellAction::GetTarget();
        if (IsTargetValid(possibleTarget))
        {
            return possibleTarget;
        }
    }

    return nullptr;
}

bool CastSpellTargetAction::IsTargetValid(Unit* target)
{
    return target &&
           bot->IsInMap(target) &&
           sServerFacade.IsFriendlyTo(bot, target) &&
           ai->IsSafe(target) &&
           (bot == target || sServerFacade.GetDistance2d(bot, target) < sPlayerbotAIConfig.sightDistance) &&
           bot->IsInGroup(target) &&
           (!aliveCheck || !target->IsDead()) &&
           (!auraCheck || !ai->HasAura(GetSpellID(), target));
}

bool CastItemTargetAction::IsTargetValid(Unit* target)
{
    if (CastSpellTargetAction::IsTargetValid(target))
    {
        if (itemAuraCheck)
        {
            const uint32 itemId = GetItemId();
            const ItemPrototype* proto = sObjectMgr.GetItemPrototype(itemId);
            if (proto)
            {
                for (uint8 i = 0; i < MAX_ITEM_PROTO_SPELLS; ++i)
                {
#ifdef MANGOSBOT_ZERO
                    if (proto->Spells[i].SpellTrigger == ITEM_SPELLTRIGGER_ON_USE || proto->Spells[i].SpellTrigger == ITEM_SPELLTRIGGER_ON_NO_DELAY_USE)
#else
                    if (proto->Spells[i].SpellTrigger == ITEM_SPELLTRIGGER_ON_USE)
#endif
                    {
                        if (proto->Spells[i].SpellId > 0 && ai->HasAura(proto->Spells[i].SpellId, target))
                        {
                            return false;
                        }
                    }
                }

                return true;
            }
        }
        else
        {
            return true;
        }
    }

    return false;
}

bool CastItemTargetAction::isUseful()
{
    const ItemPrototype* proto = sObjectMgr.GetItemPrototype(GetItemId());
    if (proto)
    {
        std::set<uint32>& skipSpells = AI_VALUE(std::set<uint32>&, "skip spells list");
        if (!skipSpells.empty())
        {
            for (int i = 0; i < MAX_ITEM_PROTO_SPELLS; ++i)
            {
                const _Spell& spellData = proto->Spells[i];
                if (spellData.SpellId)
                {
                    if (skipSpells.find(spellData.SpellId) != skipSpells.end())
                    {
                        return false;
                    }
                }
            }
        }

        return true;
    }

    return false;
}

bool CastItemTargetAction::isPossible()
{
    uint32 itemId = GetItemId();
    if (!itemId)
        return false;

    ItemPrototype const* proto = sObjectMgr.GetItemPrototype(itemId);

    if (!proto)
        return false;

    if (HasSpellCooldown(itemId))
        return false;

    if (!ai->HasCheat(BotCheatMask::item) && !bot->HasItemCount(itemId, 1))
        return false;

    uint32 spellCount = 0;

    for (int i = 0; i < MAX_ITEM_PROTO_SPELLS; ++i)
    {
        _Spell const& spellData = proto->Spells[i];

        // no spell
        if (!spellData.SpellId)
            continue;

        // wrong triggering type
#ifdef MANGOSBOT_ZERO
        if (spellData.SpellTrigger != ITEM_SPELLTRIGGER_ON_USE && spellData.SpellTrigger != ITEM_SPELLTRIGGER_ON_NO_DELAY_USE)
#else
        if (spellData.SpellTrigger != ITEM_SPELLTRIGGER_ON_USE)
#endif
            continue;

        SpellEntry const* spellInfo = sSpellTemplate.LookupEntry<SpellEntry>(spellData.SpellId);
        if (!spellInfo)
        {
            continue;
        }

        spellCount++;
    }

    return spellCount;
}

bool CastItemTargetAction::Execute(Event& event)
{
    uint32 itemId = GetItemId();
    Unit* target = GetTarget();
    ItemPrototype const* proto = sObjectMgr.GetItemPrototype(itemId);

    if (!proto)
        return false;

    Item* item = nullptr;

    if (!ai->HasCheat(BotCheatMask::item)) //If bot has no item cheat it needs an item to cast.
    {
        std::list<Item*> items = AI_VALUE2(std::list<Item*>, "inventory items", chat->formatQItem(itemId));

        if (items.empty())
            return false;

        item = items.front();
    }

    SpellCastTargets targets;
    if (target)
    {
        targets.setUnitTarget(target);
        targets.setDestination(target->GetPositionX(), target->GetPositionY(), target->GetPositionZ());
    }
    else
        targets.m_targetMask = TARGET_FLAG_SELF;

    // use triggered flag only for items with many spell casts and for not first cast
    int count = 0;

    for (int i = 0; i < MAX_ITEM_PROTO_SPELLS; ++i)
    {
        _Spell const& spellData = proto->Spells[i];

        // no spell
        if (!spellData.SpellId)
            continue;

        // wrong triggering type
#ifdef MANGOSBOT_ZERO
        if (spellData.SpellTrigger != ITEM_SPELLTRIGGER_ON_USE && spellData.SpellTrigger != ITEM_SPELLTRIGGER_ON_NO_DELAY_USE)
#else
        if (spellData.SpellTrigger != ITEM_SPELLTRIGGER_ON_USE)
#endif
            continue;

        SpellEntry const* spellInfo = sSpellTemplate.LookupEntry<SpellEntry>(spellData.SpellId);
        if (!spellInfo)
        {
            continue;
        }

        if (spellInfo->Targets & TARGET_FLAG_DEST_LOCATION)
            targets.m_targetMask = TARGET_FLAG_DEST_LOCATION;

        BotUseItemSpell* spell = new BotUseItemSpell(bot, spellInfo, (count > 0) ? TRIGGERED_OLD_TRIGGERED : TRIGGERED_NONE);

        Item* tItem = nullptr;

        if (item)
        {
            spell->SetCastItem(item);
            item->SetUsedInSpell(true);
        }

        spell->m_clientCast = true;

        bool result = (spell->ForceSpellStart(&targets) == SPELL_CAST_OK);

        if (!result)
            return false;

        if (ai->HasCheat(BotCheatMask::item))
        {
            if (!HasSpellCooldown(itemId))
            {
                bot->RemoveSpellCooldown(*spellInfo, false);
                bot->AddCooldown(*spellInfo, proto, false);
            }
        }

        ++count;
    }

    return count;
}

bool CastItemTargetAction::HasSpellCooldown(uint32 itemId)
{
    ItemPrototype const* proto = sObjectMgr.GetItemPrototype(itemId);

    if (!proto)
        return false;

    uint32 spellId = 0;
    for (uint8 i = 0; i < MAX_ITEM_PROTO_SPELLS; ++i)
    {
        if (proto->Spells[i].SpellTrigger != ITEM_SPELLTRIGGER_ON_USE)
        {
            continue;
        }

        if (proto->Spells[i].SpellId > 0)
        {
            if (!sServerFacade.IsSpellReady(bot, proto->Spells[i].SpellId))
                return true;

            if (!sServerFacade.IsSpellReady(bot, proto->Spells[i].SpellId, itemId))
                return true;
        }
    }

    return false;
}
