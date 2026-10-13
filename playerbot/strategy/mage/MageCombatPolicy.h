#pragma once
#include "playerbot/AiFactory.h"

namespace ai
{
    inline bool ClassicMageFrostPrimary(PlayerbotAI* ai)
    {
#ifdef MANGOSBOT_ZERO
        if (ai->IsInPvp()) return false;
        const auto tabs = AiFactory::GetPlayerSpecTabs(ai->GetBot());
        const auto frost = tabs.at(2);
        // Both the deep-Frost build and the Arcane Power/Frost raid hybrid
        // sustain Frostbolt. Strategy selection by the largest tree must not
        // turn the hybrid into an Arcane Missiles rotation.
        return frost >= 15 && (ai->GetBot()->HasSpell(12042) ||
            (frost >= tabs.at(0) && frost >= tabs.at(1)));
#else
        return false;
#endif
    }

    inline bool MageFrostRotation(PlayerbotAI* ai)
    {
        return ai->HasStrategy("frost raid",BotState::BOT_STATE_COMBAT) ||
            ai->HasStrategy("frost pve",BotState::BOT_STATE_COMBAT) ||
            ai->HasStrategy("frost",BotState::BOT_STATE_COMBAT) || ClassicMageFrostPrimary(ai);
    }

    inline const char* MagePrimaryDamageSpell(PlayerbotAI* ai)
    {
        if (MageFrostRotation(ai)) return "frostbolt";
        if (ai->HasStrategy("fire raid",BotState::BOT_STATE_COMBAT) ||
            ai->HasStrategy("fire pve",BotState::BOT_STATE_COMBAT) || ai->HasStrategy("fire",BotState::BOT_STATE_COMBAT)) return "fireball";
        if (ai->HasStrategy("arcane raid",BotState::BOT_STATE_COMBAT) ||
            ai->HasStrategy("arcane pve",BotState::BOT_STATE_COMBAT) || ai->HasStrategy("arcane",BotState::BOT_STATE_COMBAT)) return "arcane missiles";
        return "frostbolt";
    }
}
