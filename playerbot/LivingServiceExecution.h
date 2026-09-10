#pragma once
#include <string>

// Called only after the caller has validated its activity and world safety.
// A stale wand/shoot pointer is not an active cast. Never cancel generic spells
// or channels, and never stop auto-repeat while a combat target still exists.
namespace LivingServiceExecution {
template<class Bot> const char* Blocker(Bot* bot) {
    if(bot->IsInCombat()) return "in_combat";
    if(bot->GetTradeData()) return "trade_in_progress";
    if(bot->IsNonMeleeSpellCasted(false, false, true)) return "active_spell_or_channel";
    if(bot->GetVictim() || !bot->getAttackers().empty()) return "combat_target_not_released";
    return "";
}
template<class Bot> bool Busy(Bot* bot) {
    return *Blocker(bot)!=0;
}
template<class Bot> bool Prepare(Bot* bot) {
    if (Busy(bot)) return false;
    if (bot->GetCurrentSpell(CURRENT_AUTOREPEAT_SPELL))
        bot->InterruptSpell(CURRENT_AUTOREPEAT_SPELL);
    return true;
}
inline bool DisruptiveMaintenance(const std::string& action) {
    return action == "random recipe" || action == "use random recipe" ||
        action == "move to fish" || action == "fish";
}
inline bool NeedsSplitPreparation(unsigned stack, unsigned amount, bool emptySlot) {
    return stack>amount && !emptySlot;
}
}
