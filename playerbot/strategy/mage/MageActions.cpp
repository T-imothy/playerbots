
#include "playerbot/playerbot.h"
#include "MageActions.h"
#include "playerbot/ServerFacade.h"
#include "Spells/SpellAuras.h"
#include "Spells/SpellMgr.h"
#include "Entities/DynamicObject.h"
#include "playerbot/strategy/CasterCombatPolicy.h"
#include "playerbot/strategy/MoltenCoreTrashPolicy.h"

using namespace ai;

namespace
{
    bool MoltenCoreMageCluster(PlayerbotAI* ai, std::vector<Unit*>& cluster, Unit*& anchor, bool& rangedOnly)
    {
#ifdef MANGOSBOT_ZERO
        Player* bot=ai->GetBot();
        if (!bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() || bot->HasCharmer() ||
            bot->GetMapId()!=409 || !bot->GetGroup() || bot->getClass()!=CLASS_MAGE ||
            ai->IsRealPlayer() || ai->IsHeal(bot) || !MoltenCoreTrashSpellAllowed(ai,"arcane explosion")) return false;
        std::vector<Unit*> engaged;
        for (ObjectGuid guid:ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
        {
            Unit* enemy=ai->GetUnit(guid);
            if (!enemy || !enemy->IsInWorld() || !enemy->IsAlive() || !bot->IsInMap(enemy) ||
                !enemy->IsInCombat() || enemy->HasCharmer() || sServerFacade.IsFriendlyTo(bot,enemy)) continue;
            if (enemy->GetEntry()==11669 || enemy->GetEntry()==11673) rangedOnly=true;
            // These encounters have their own separation/CC routines; a close
            // AoE preference must never override them.
            if (enemy->GetEntry()==11982 || enemy->GetEntry()==12056 || enemy->GetEntry()==12264 ||
                enemy->GetEntry()==11988 || enemy->GetEntry()==12018 || enemy->GetEntry()==11502 ||
                enemy->GetEntry()==12057 || enemy->GetEntry()==12099) return false;
            if (enemy->GetEntry()==11671 && enemy->HasAura(19951)) continue;
            if (PossibleAttackTargetsValue::HasBreakableCC(enemy,bot) ||
                PossibleAttackTargetsValue::HasUnBreakableCC(enemy,bot)) continue;
            Unit* victim=enemy->GetVictim();
            const bool held=victim && victim->IsPlayer() && victim->IsInWorld() && victim->IsAlive() &&
                bot->IsInMap(victim) && !static_cast<Player*>(victim)->IsBeingTeleported() &&
                !victim->HasCharmer() && static_cast<Player*>(victim)->GetGroup()==bot->GetGroup() &&
                ai->IsTank(static_cast<Player*>(victim));
            if (held || MoltenCoreRecoverableImp(ai,enemy)) engaged.push_back(enemy);
        }
        std::sort(engaged.begin(),engaged.end(),[](Unit* a,Unit* b){return a->GetObjectGuid()<b->GetObjectGuid();});
        for (Unit* candidate:engaged)
        {
            std::vector<Unit*> neighbours;
            for (Unit* enemy:engaged)
                if (candidate->GetDistance(enemy)<=6 && std::fabs(candidate->GetPositionZ()-enemy->GetPositionZ())<=4)
                    neighbours.push_back(enemy);
            if (neighbours.size()>cluster.size()) {cluster=neighbours;anchor=candidate;}
        }
        return anchor && cluster.size()>=2 && CasterAreaSafe(ai,anchor,12);
#else
        return false;
#endif
    }

    unsigned MoltenCoreMageHits(PlayerbotAI* ai, const std::vector<Unit*>& cluster, SpellSchoolMask school, bool cone)
    {
        Player* bot=ai->GetBot();unsigned count=0;
        for (Unit* enemy:cluster)
        {
            const float dx=enemy->GetPositionX()-bot->GetPositionX(),dy=enemy->GetPositionY()-bot->GetPositionY();
            const float dz=enemy->GetPositionZ()-bot->GetPositionZ();
            // Conservative centre radius; native spell admission/effects stay
            // authoritative for hit boxes, immunities and the frontal cone.
            if (dx*dx+dy*dy+dz*dz>9*9 || enemy->IsImmuneToDamage(school) ||
                (cone && std::cos(std::atan2(dy,dx)-bot->GetOrientation())<0.7071f)) continue;
            ++count;
        }
        return count;
    }
}

bool ai::PlanMoltenCoreMageCleave(PlayerbotAI* ai, EncounterPosition& plan)
{
    std::vector<Unit*> cluster;Unit* anchor=nullptr;bool rangedOnly=false;
    if (!MoltenCoreMageCluster(ai,cluster,anchor,rangedOnly) || rangedOnly) return false;
    Player* bot=ai->GetBot();
    plan.active=true;plan.spell=1449;plan.map=bot->GetMapId();plan.instance=bot->GetInstanceId();
    plan.boss=anchor->GetObjectGuid();
    // A legal existing cleave station stays fixed while casting. Hound/Surger
    // tank stacks are selected earlier and remain authoritative.
    if (MoltenCoreMageHits(ai,cluster,SPELL_SCHOOL_MASK_ARCANE,false)>=2)
        plan.destination={bot->GetPositionX(),bot->GetPositionY(),bot->GetPositionZ()};
    else
    {
        const float rear=anchor->GetOrientation()+float(M_PI);
        plan.destination={anchor->GetPositionX()+std::cos(rear)*2,
            anchor->GetPositionY()+std::sin(rear)*2,anchor->GetPositionZ()};
    }
    if (CasterAreaSafe(ai,plan.destination.x,plan.destination.y,plan.destination.z,12) &&
        ValidateEncounterDestination(ai,plan)) return true;
    plan.active=false;return false;
}

Action* MoltenCoreMageAoeAction::Select()
{
    std::vector<Unit*> cluster;Unit* anchor=nullptr;bool rangedOnly=false;
    if (!MoltenCoreMageCluster(ai,cluster,anchor,rangedOnly)) return nullptr;
    auto ready=[&](const char* name)->Action* {
        Action* action=ai->GetAiObjectContext()->GetAction(name);
        return action && action->isUseful() && action->isPossible() &&
            CasterSpellAreaSafe(ai,name,action->GetTarget()) ? action : nullptr;
    };
    // Never walk a mage into imp pulses or a patrolling Ancient Core Hound.
    if (rangedOnly) return ready("blizzard");
    if (MoltenCoreMageHits(ai,cluster,SPELL_SCHOOL_MASK_ARCANE,false)<2) return ready("blizzard");
    bool ownField=false;
    const uint32 flame=CasterSpell(ai,"flamestrike");
    for (ObjectGuid guid:ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("nearest dynamic objects no los")->Get())
        if (DynamicObject* field=bot->GetMap()->GetDynamicObject(guid))
            if (field->GetCasterGuid()==bot->GetObjectGuid() && field->GetSpellId()==flame &&
                field->GetDuration()>0 && field->IsAffecting(anchor)) {ownField=true;break;}
    if (!ownField && !anchor->IsImmuneToDamage(SPELL_SCHOOL_MASK_FIRE))
        if (Action* action=ready("flamestrike")) return action;
    if (MoltenCoreMageHits(ai,cluster,SPELL_SCHOOL_MASK_FROST,true)>=2)
        if (Action* action=ready("cone of cold")) return action;
    if (Action* action=ready("arcane explosion")) return action;
    return ready("blizzard");
}

bool MoltenCoreMageAoeAction::isUseful() { return Select()!=nullptr; }

bool MoltenCoreMageAoeAction::Execute(Event& event)
{
    Action* action=Select();
    if (!action || !action->Execute(event)) return false;
    SetDuration(action->GetDuration()); // Preserve native GCD/cast/channel wait.
    return true;
}

bool CastSpellstealAction::HasStealableAura(PlayerbotAI* ai, Unit* target, const SpellEntry* spell)
{
#ifndef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        !target || target == bot || !target->IsInWorld() || !target->IsAlive() ||
        !bot->IsInMap(target) || !spell || !bot->CanAttackSpell(target, spell)) return false;
    uint32 mask = 0;
    for (unsigned effect = 0; effect < MAX_EFFECT_INDEX; ++effect)
        if (spell->Effect[effect] == SPELL_EFFECT_STEAL_BENEFICIAL_BUFF &&
            spell->EffectMiscValue[effect] >= 0 && spell->EffectMiscValue[effect] <= DISPEL_ZG_TICKET)
            mask |= GetDispellMask(DispelType(spell->EffectMiscValue[effect]));
    if (!mask) return false;
    // Match native EffectStealBeneficialBuff's holder predicate. Ordinary
    // dispellability alone does not mean a buff can be stolen. Native CheckCast
    // does not test this pool, so a no-op cast can otherwise consume mana/GCD.
    for (const auto& aura : target->GetSpellAuraHolderMap())
    {
        const SpellAuraHolder* holder = aura.second;
        if (!holder || !holder->IsPositive() || holder->IsPassive()) continue;
        const SpellEntry* entry = holder->GetSpellProto();
        if (!entry || entry->Dispel > DISPEL_ZG_TICKET || !(mask & (1u << entry->Dispel)) ||
            entry->HasAttribute(SPELL_ATTR_EX4_CANNOT_BE_STOLEN)) continue;
        const int32 remaining = holder->GetAuraDuration();
        if (sPlayerbotAIConfig.dispelAuraDuration && remaining > 0 &&
            remaining < (int32)sPlayerbotAIConfig.dispelAuraDuration) continue;
        return true;
    }
#endif
    return false;
}

bool CastSpellstealAction::isUseful()
{
    return CastSpellAction::isUseful() && HasStealableAura(ai, GetTarget(), sServerFacade.LookupSpellInfo(GetSpellID()));
}

bool CastSpellstealAction::Execute(Event& event)
{
    RefreshSpellId();
    return HasStealableAura(ai, GetTarget(), sServerFacade.LookupSpellInfo(GetSpellID())) && CastSpellAction::Execute(event);
}
