#include "playerbot/playerbot.h"
#include "playerbot/PlayerbotPartyCombatCoordinator.h"
#include "LivingPartyCombatStrategy.h"

using namespace ai;

float LivingPartyCombatMultiplier::GetValue(Action* action)
{
    return sPlayerbotPartyCombatCoordinator.ActionMultiplier(ai->GetBot(), action);
}

void LivingPartyCombatStrategy::InitCombatMultipliers(std::list<Multiplier*>& multipliers)
{
    multipliers.push_back(new LivingPartyCombatMultiplier(ai));
}

NextAction** LivingPartyHealerOffDpsStrategy::GetDefaultCombatActions()
{
    // Give mixed-party healers a restrained, class-appropriate filler instead
    // of leaving them idle or forcing every caster into melee. The coordinator
    // multiplier suppresses these actions whenever healing is needed, mana is
    // reserved, threat is unsafe, or the target is not approved.
    switch (ai->GetBot()->getClass())
    {
        case CLASS_DRUID:
            return NextAction::array(0, new NextAction("wrath", ACTION_IDLE),
                new NextAction("melee", ACTION_IDLE - 1), NULL);
        case CLASS_SHAMAN:
            return NextAction::array(0, new NextAction("lightning bolt", ACTION_IDLE),
                new NextAction("melee", ACTION_IDLE - 1), NULL);
        case CLASS_PRIEST:
            return NextAction::array(0, new NextAction("smite", ACTION_IDLE),
                new NextAction("shoot", ACTION_IDLE - 1),
                new NextAction("melee", ACTION_IDLE - 2), NULL);
        case CLASS_PALADIN:
            return NextAction::array(0, new NextAction("melee", ACTION_IDLE), NULL);
        default:
            return NULL;
    }
}
