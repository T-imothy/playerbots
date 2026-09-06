
#include "playerbot/playerbot.h"
#include "GenericTriggers.h"
#include "CureTriggers.h"
#include "playerbot/strategy/actions/WorldBuffAction.h"
#include "playerbot/strategy/actions/EncounterSpellPolicy.h"
#include "playerbot/ServerFacade.h"

using namespace ai;

bool NeedCureTrigger::IsActive() 
{
    Unit* target = GetTarget();
    return target && ai->HasAuraToDispel(target, dispelType) &&
        !ShouldAvoidEncounterDispel(ai, sServerFacade.LookupSpellInfo(AI_VALUE2(uint32, "spell id", spell)), target);
}

Value<Unit*>* PartyMemberNeedCureTrigger::GetTargetValue()
{
    return context->GetValue<Unit*>("party member to dispel", std::to_string(dispelType) + "," + spell);
}

bool NeedWorldBuffTrigger::IsActive()
{
    return !WorldBuffAction::NeedWorldBuffs(bot).empty();   
}
