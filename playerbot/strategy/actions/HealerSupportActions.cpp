#include "playerbot/playerbot.h"
#include "HealerSupportActions.h"
#include "EncounterSpellPolicy.h"
#include "playerbot/ServerFacade.h"

using namespace ai;

bool ai::HasHealingPressure(PlayerbotAI* ai, uint32 healthThreshold)
{
    Player* bot = ai->GetBot();
    Unit* patient = AI_VALUE(Unit*, "party member to heal");
    const auto needsHeal = [&](Unit* unit) {
        return unit && unit->IsInWorld() && unit->IsAlive() && unit->GetMaxHealth() && bot->IsInMap(unit) &&
            (unit->GetHealthPercent() < healthThreshold || NeedsFullHealingToRemoveAura(unit) || RemainingHealingAbsorb(unit));
    };
    return needsHeal(bot) || needsHeal(patient);
}

Unit* ai::SelectHealerSupportTarget(PlayerbotAI* ai, const std::string& spell, float range)
{
    Player* bot = ai->GetBot();
    if (!bot->IsInWorld() || !bot->IsAlive() || !ai->HasSpell(spell)) return nullptr;
    Group* group = bot->GetGroup();
    if (!group) return nullptr;
    Player* best = nullptr;
    int bestPriority = 4;
    for (GroupReference* ref = group->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || !ai->IsSafe(member) || !member->IsInWorld() || !member->IsAlive() ||
            member->IsBeingTeleported() || !bot->IsInMap(member) ||
            !sServerFacade.IsFriendlyTo(bot, member)) continue;
#ifdef MANGOSBOT_TWO
        if (!(bot->GetPhaseMask() & member->GetPhaseMask())) continue;
#endif
        // Preserve this caster's existing assignment, including Prayer of
        // Mending after a jump, even if that member is currently out of range.
        if (ai->HasMyAura(spell, member)) return nullptr;
        // Never alternate Earth Shield and Water Shield on the healer itself.
        if (member == bot || member->duel || sServerFacade.GetDistance2d(bot, member) > range ||
            ai->HasAura(spell, member)) continue;
        const int priority = ai->IsTank(member) ? 0 : !member->getAttackers().empty() ? 1 :
            member == ai->GetMaster() ? 2 : 3;
        if (priority < bestPriority) { best = member; bestPriority = priority; }
    }
    return best;
}

bool CastUrgentHealingBuffAction::isUseful()
{
    if (GetSpellName() == "tidal force" && HasHealingPressure(ai, sPlayerbotAIConfig.criticalHealth)) return false;
    return HasHealingPressure(ai, sPlayerbotAIConfig.lowHealth) && CastBuffSpellAction::isUseful();
}

bool CastNaturesSwiftnessHealAction::isUseful()
{
    Unit* target = GetTarget();
    return target && target->GetHealthPercent() < sPlayerbotAIConfig.criticalHealth &&
        (ai->HasAura("nature's swiftness", bot) || ai->CanCastSpell("nature's swiftness", bot)) &&
        CastHealingSpellAction::isUseful();
}

NextAction** CastNaturesSwiftnessHealAction::getPrerequisites()
{
    NextAction** prerequisites = NextAction::array(0, new NextAction("nature's swiftness"), NULL);
    if (bot->getClass() == CLASS_DRUID)
        prerequisites = NextAction::merge(NextAction::array(0, new NextAction("restoration caster form"), NULL), prerequisites);
    return NextAction::merge(prerequisites, CastHealingSpellAction::getPrerequisites());
}

#ifdef MANGOSBOT_TWO
bool CastHymnOfHopeAction::isUseful()
{
    return bot->GetMaxPower(POWER_MANA) &&
        uint64(bot->GetPower(POWER_MANA)) * 100 < uint64(bot->GetMaxPower(POWER_MANA)) * sPlayerbotAIConfig.lowMana &&
        !sServerFacade.isMoving(bot) && bot->getAttackers().empty() &&
        !HasHealingPressure(ai, sPlayerbotAIConfig.mediumHealth) && CastBuffSpellAction::isUseful();
}

bool CastHymnOfHopeAction::Execute(Event& event)
{
    return isUseful() && CastBuffSpellAction::Execute(event);
}

bool StopHymnOfHopeAction::isUseful()
{
    const Spell* spell = bot->GetCurrentSpell(CURRENT_CHANNELED_SPELL);
    return spell && spell->m_spellInfo && spell->m_spellInfo->Id == 64901 &&
        (!bot->getAttackers().empty() || HasHealingPressure(ai, sPlayerbotAIConfig.lowHealth));
}

bool StopHymnOfHopeAction::Execute(Event& event)
{
    if (!isUseful()) return false;
    bot->InterruptSpell(CURRENT_CHANNELED_SPELL);
    SetDuration(0);
    return true;
}
#endif
