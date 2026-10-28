#include "playerbot/playerbot.h"
#include "RaidPetAdmission.h"
#include "ClassicRaidActions.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

namespace
{
    PlayerbotAI* RaidPetOwner(Unit* pet)
    {
        if (!pet || !pet->IsInWorld() || !pet->IsAlive() || pet->HasCharmer() || pet->GetMapId() != 533) return nullptr;
        Unit* ownerUnit = pet->GetOwner();
        if (!ownerUnit || !ownerUnit->IsPlayer() || !ownerUnit->IsInWorld() || !ownerUnit->IsAlive() || !pet->IsInMap(ownerUnit)) return nullptr;
        Player* owner = static_cast<Player*>(ownerUnit);
        if (owner->GetPet() != pet || owner->HasCharmer() || owner->IsBeingTeleported() || !owner->IsInCombat() || !owner->GetGroup()) return nullptr;
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
    if (!spell || (ClassicRaidDamageSpell(spell) && !IsPositiveSpell(spell, pet, target)))
        if (brain->GetAiObjectContext()->GetValue<ClassicRaidPlan>("classic raid plan")->Get().holdDamage) return false;
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
