#pragma once
#include "GenericSpellActions.h"

namespace ai
{
    class CastQuelDoreiMeditationAction : public CastBuffSpellAction
    {
    public:
        CastQuelDoreiMeditationAction(PlayerbotAI* ai) : CastBuffSpellAction(ai, "quel'dorei meditation") {}
        bool isUseful() override
        {
            if (bot->getRace() != RACE_HIGH_ELF || !CastBuffSpellAction::isUseful())
                return false;
            // The native starting spells supply different effects to warriors,
            // rogues and mana classes under the same localized spell name.
            switch (bot->getPowerType())
            {
            case POWER_RAGE:
                return bot->IsInCombat() && bot->GetPower(POWER_RAGE) < 400;
            case POWER_ENERGY:
                return bot->IsInCombat() && bot->GetPower(POWER_ENERGY) < 40;
            case POWER_MANA:
                return bot->GetMaxPower(POWER_MANA) &&
                    bot->GetPower(POWER_MANA) * 100 / bot->GetMaxPower(POWER_MANA) < 40;
            default:
                return false;
            }
        }
    };

    class CastGoblinExitStrategyAction : public CastBuffSpellAction
    {
    public:
        CastGoblinExitStrategyAction(PlayerbotAI* ai) : CastBuffSpellAction(ai, "exit strategy") {}
        bool isUseful() override
        {
            // This racial pacifies and silences the caster. Use it only in the
            // existing emergency-flee policy, never as an ordinary combat buff.
            return bot->getRace() == RACE_GOBLIN && bot->IsInCombat() &&
                ai->HasStrategy("flee", BotState::BOT_STATE_COMBAT) &&
                !bot->IsNonMeleeSpellCasted(true) && CastBuffSpellAction::isUseful();
        }
    };
}
