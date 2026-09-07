#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"

using namespace ai;

MoamManaControlAction::MoamManaControlAction(PlayerbotAI* ai) : CastSpellAction(ai,
    ai->GetBot()->getClass() == CLASS_WARLOCK ? "drain mana" :
    ai->GetBot()->getClass() == CLASS_PRIEST ? "mana burn" :
    ai->GetBot()->getClass() == CLASS_HUNTER ? "viper sting" : "")
{
}

bool MoamManaControlAction::isUseful()
{
    if (bot->GetMapId() != 509 || !bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() ||
        !bot->GetGroup() || bot->HasCharmer() || bot->IsBeingTeleported() || ai->IsRealPlayer() ||
        ai->IsHeal(bot) || ai->IsTank(bot) || GetSpellName().empty()) return false;
    Unit* target = GetTarget();
    if (!target || target->GetEntry() != 15340 || !target->IsInWorld() || !target->IsAlive() ||
        !target->IsInCombat() || target->HasCharmer() || !bot->IsInMap(target) ||
        !target->GetMaxPower(POWER_MANA) || target->HasAura(25685) ||
        uint64(target->GetPower(POWER_MANA)) * 4 < target->GetMaxPower(POWER_MANA)) return false;
    // Avoid refreshing a sting already draining him. During Energize the
    // summoned fiends take priority, while healers keep their healing role.
    if (GetSpellName() == "viper sting" && ai->HasAura("viper sting", target)) return false;
    return CastSpellAction::isUseful();
}

bool MoamManaControlAction::Execute(Event& event)
{
    // Recheck the current phase/target before the standard learned-rank cast.
    return isUseful() && CastSpellAction::Execute(event);
}
