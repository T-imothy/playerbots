#include "playerbot/playerbot.h"
#include "EncounterSpellPolicy.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/ServerFacade.h"

bool ai::NeedsRaidObjectiveHealing(Unit* target)
{
#ifdef MANGOSBOT_TWO
    return target && target->IsInWorld() && target->IsAlive() && target->IsInCombat() &&
        !target->HasCharmer() && target->GetMapId() == 631 && target->GetEntry() == 36789 &&
        target->GetMaxHealth() && target->GetHealth() < target->GetMaxHealth();
#else
    return false;
#endif
}

Unit* ai::FindRaidHealingObjective(PlayerbotAI* ai)
{
#ifdef MANGOSBOT_TWO
    Player* bot = ai->GetBot();
    if (!bot || bot->GetMapId() != 631 || !bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() ||
        bot->HasCharmer() || bot->IsBeingTeleported() || !bot->GetGroup() || ai->IsRealPlayer() ||
        !ai->IsHeal(bot) || ai->HasStrategy("focus heal targets", BotState::BOT_STATE_COMBAT)) return nullptr;
    Unit* objective = nullptr;
    for (const auto& guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets", "100:1")->Get())
    {
        Unit* unit = ai->GetUnit(guid);
        if (!NeedsRaidObjectiveHealing(unit) || !bot->IsInMap(unit) ||
            !sServerFacade.IsFriendlyTo(bot, unit) || bot->GetDistance(unit) > ai->GetRange("heal")) continue;
        if (objective && objective != unit) return nullptr;
        objective = unit;
    }
    if (!objective) return nullptr;

    // Keep one available bot healer on the raid when there are several. Prefer
    // the least-buffed healer for that role, so native Dream stacks contribute
    // to the objective. Read native player state, not another bot's AI values.
    Player* raidHealer = nullptr;
    uint32 leastStacks = 0;
    unsigned count = 0;
    for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
    {
        Player* healer = ref->getSource();
        if (!healer || !healer->IsInWorld() || !healer->IsAlive() || !bot->IsInMap(healer) ||
            healer->HasCharmer() || healer->IsBeingTeleported() || healer->GetGroup() != bot->GetGroup() ||
            !healer->GetPlayerbotAI() || healer->GetPlayerbotAI()->IsRealPlayer() || !ai->IsHeal(healer) ||
            !healer->GetPower(POWER_MANA) || healer->GetDistance(objective) > ai->GetRange("heal")) continue;
        uint32 stacks = 0;
        for (uint32 id : {70873u, 71941u})
            if (const SpellAuraHolder* aura = healer->GetSpellAuraHolder(id)) stacks += aura->GetStackAmount();
        ++count;
        if (!raidHealer || stacks < leastStacks ||
            (stacks == leastStacks && healer->GetObjectGuid() < raidHealer->GetObjectGuid()))
        {
            raidHealer = healer;
            leastStacks = stacks;
        }
    }
    if (!count || !bot->GetPower(POWER_MANA) || (count > 1 && raidHealer == bot)) return nullptr;
    return objective;
#else
    return nullptr;
#endif
}
