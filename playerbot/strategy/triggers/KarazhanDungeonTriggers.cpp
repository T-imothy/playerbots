
#include "playerbot/playerbot.h"
#include "KarazhanDungeonTriggers.h"
#include "GenericTriggers.h"
#include "playerbot/strategy/actions/KarazhanDungeonActions.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;

bool KarazhanPriorityTargetTrigger::IsActive()
{
    KarazhanPriorityTargetAction action(ai);
    return action.isUseful();
}

bool AranFlameWreathTrigger::IsActive()
{
    AranFlameWreathHoldAction action(ai);
    return action.isUseful();
}

bool NetherspiteBeamPositionTrigger::IsActive()
{
    EncounterPosition plan;
    return NetherspitePositionAction::GetPlan(ai, plan) &&
        bot->GetDistance(plan.destination.x, plan.destination.y, plan.destination.z) > 1.0f;
}

bool PrinceMalchezaarTooCloseTrigger::IsActive()
{
    if (!bot->IsInWorld() || !bot->IsAlive() || bot->HasCharmer() || bot->IsBeingTeleported() ||
        bot->GetMapId() != 532 || !bot->IsInCombat()) return false;
    PullStrategy* strategy = PullStrategy::Get(ai);
    if (strategy && strategy->HasPullStarted())
        return false;
    Unit* target = nullptr;
    for (const auto& guid : AI_VALUE(std::list<ObjectGuid>, "attackers"))
    {
        Unit* unit = ai->GetUnit(guid);
        if (unit && unit->GetEntry() == 15690 && unit->IsInWorld() && bot->IsInMap(unit) &&
            unit->IsAlive() && unit->IsInCombat()) { target = unit; break; }
    }
    if (!target) return false;
    if (bot->HasAura(30843) || (EnfeeblePart() && target && target->GetVictim() != bot) || MeleeWaitCheck(target)) 
        return true;
    if (ai->IsRanged(bot, true))
        return CloseToCreatureTrigger::IsActive();
    return false;
}

bool PrinceMalchezaarTooCloseTrigger::MeleeWaitCheck(Unit* target)
{
    // Check if we should be someone staying out of Shadow Nova blast
    if (target && target->GetHealthPercent() > 30.0f && target->IsCreature())
    {
        if (ai->IsMelee(bot, true) && target->GetVictim() != bot && target->GetDistance(bot) > 8.0f)
        {
            if (Spell const* genericSpell = target->GetCurrentSpell(CURRENT_GENERIC_SPELL))
            {
                if (genericSpell->m_spellInfo->Id == 30852 && genericSpell->getState() != SPELL_STATE_FINISHED)
                    return true;
            }
        }
    }

    return false;
}

bool PrinceMalchezaarTooCloseTrigger::EnfeeblePart()
{
    Group* group = bot->GetGroup();
    if (!group)
        return false;

    for (GroupReference* ref = group->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->getSource();
        if (!member || !member->IsInWorld() || member->IsBeingTeleported() || !bot->IsInMap(member) || !sServerFacade.IsAlive(member))
            continue;

        if (member->HasAura(30843))
            return true;
    }
    return false;
}
