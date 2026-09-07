#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

uint32 ColdMovementAction::GetColdStacks() const
{
#ifdef MANGOSBOT_TWO
    if (!bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() || bot->HasCharmer() ||
        bot->IsBeingTeleported() || !bot->GetGroup() || ai->IsRealPlayer() || !ai->CanMove() || ai->IsJumping()) return 0;
    uint32 entry = 0, aura = 0;
    if (bot->GetMapId() == 576) { entry = 26723; aura = 48095; }
    else if (bot->GetMapId() == 603 && !bot->HasAura(62821)) { entry = 32845; aura = 62039; }
    else return 0;
    const SpellAuraHolder* cold = bot->GetSpellAuraHolder(aura);
    if (!cold || cold->GetStackAmount() < 2) return 0;
    for (const auto& guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("attackers")->Get())
    {
        Unit* boss = ai->GetUnit(guid);
        if (!boss || !boss->IsInWorld() || !boss->IsAlive() || !boss->IsInCombat() ||
            boss->HasCharmer() || !bot->IsInMap(boss) || boss->GetEntry() != entry || bot->GetDistance(boss) > 100) continue;
        // Flash Freeze positioning takes precedence over an optional jump.
        const Spell* cast = boss->GetCurrentSpell(CURRENT_GENERIC_SPELL);
        if (entry == 32845 && cast && cast->m_spellInfo && cast->getState() == SPELL_STATE_CASTING && cast->m_spellInfo->Id == 61968) return 0;
        return cold->GetStackAmount();
    }
#endif
    return 0;
}

bool ColdMovementAction::isUseful()
{
    return GetColdStacks() >= 2;
}

bool ColdMovementAction::ShouldReactionInterruptCast() const
{
    // Finish an ordinary cast at low stacks. Escalate only when native damage
    // has compounded; no aura removal, immunity or synthetic movement flags.
    return GetColdStacks() >= 4;
}

bool ColdMovementAction::Execute(Event& event)
{
    if (!isUseful()) return false;
    Qualify("inplace");
    // Reuse the normal jump's terrain, landing, packet and movement handling.
    // JumpAction still declines an uncommanded jump during an active cast.
    return JumpAction::Execute(event);
}
