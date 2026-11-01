#include "playerbot/playerbot.h"
#include "RaidPetAdmission.h"
#include "ClassicRaidActions.h"
#include "EncounterSpellPolicy.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

namespace
{
    PlayerbotAI* RaidPetOwner(Unit* pet)
    {
        if (!pet || !pet->IsInWorld() || !pet->IsAlive() || pet->HasCharmer()) return nullptr;
        if(pet->GetMapId()!=533
#ifdef MANGOSBOT_ZERO
            && pet->GetMapId()!=509 && pet->GetMapId()!=469 && pet->GetMapId()!=409
#endif
            )return nullptr;
        Unit* ownerUnit = pet->GetOwner();
        if (!ownerUnit || !ownerUnit->IsPlayer() || !ownerUnit->IsInWorld() || !ownerUnit->IsAlive() || !pet->IsInMap(ownerUnit)) return nullptr;
        Player* owner = static_cast<Player*>(ownerUnit);
        if (owner->GetPet() != pet || owner->HasCharmer() || owner->IsBeingTeleported() || !owner->GetGroup()) return nullptr;
        PlayerbotAI* brain = owner->GetPlayerbotAI();
        return brain && !brain->IsRealPlayer() ? brain : nullptr;
    }
}

bool ai::RaidPetOffenseAllowed(Unit* pet, const SpellEntry* spell, Unit* target)
{
    // Native pet ticks/callbacks share their owner's serialized map update.
    // Map::Update joins its idle-bot batch and grid discovery before updating
    // creatures; pet command packets are processed in the world phase before
    // map workers. Never reuse this context-reading hook from an async worker.
    PlayerbotAI* brain = RaidPetOwner(pet);
    if (!brain || (target && (!target->IsInWorld() || !pet->IsInMap(target)))) return true;
    if (!brain->GetBot()->IsInCombat())
    {
#ifdef MANGOSBOT_ZERO
        // Phase-one wave summons can clear the hunter's combat flag before
        // his pet receives its attack command. The native instance/channel
        // gate remains authoritative through that transition: otherwise the
        // pet chases a soldier into the passive alcoves before combat resumes.
        if (pet->GetMapId() == 533 &&
            (!spell || (ClassicRaidDamageSpell(spell) && !IsPositiveSpell(spell, pet, target))))
            return KelthuzadOpeningApproachAllowed(brain, target, true);
#endif
        return true; // Preserve the other encounters' out-of-combat behavior.
    }
#ifdef MANGOSBOT_ZERO
    if (pet->GetMapId()==409)
    {
        if (spell && (!ClassicRaidDamageSpell(spell) || IsPositiveSpell(spell,pet,target))) return true;
        if (MajordomoPolymorphReserved(brain,target)) return false;
        bool area=spell && (IsAreaOfEffectSpell(spell) || spell->MaxAffectedTargets>1);
        if (spell) for (uint32 count:spell->EffectChainTarget) if (count>1) area=true;
        if (area)
            for (const ObjectGuid guid:brain->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets", "100:1")->Get())
                if (MajordomoPolymorphReserved(brain,brain->GetUnit(guid))) return false;
        return true;
    }
#endif
    if (!spell || (ClassicRaidDamageSpell(spell) && !IsPositiveSpell(spell, pet, target)))
    {
        if (!KelthuzadOpeningApproachAllowed(brain,target,true)) return false;
        if (brain->GetAiObjectContext()->GetValue<ClassicRaidPlan>("classic raid plan")->Get().holdDamage) return false;
    }
    return ClassicRaidOffenseAllowed(brain, spell, target);
}

void ai::StopUnsafeRaidPetCasts(Unit* pet)
{
    if (!RaidPetOwner(pet)) return;
    for (auto slot : {CURRENT_GENERIC_SPELL, CURRENT_CHANNELED_SPELL, CURRENT_AUTOREPEAT_SPELL})
        if (Spell* cast = pet->GetCurrentSpell(slot))
            if (cast->getState() != SPELL_STATE_FINISHED && cast->m_spellInfo &&
                !RaidPetOffenseAllowed(pet, cast->m_spellInfo, cast->m_targets.getUnitTarget()))
                pet->InterruptSpell(slot);
}
