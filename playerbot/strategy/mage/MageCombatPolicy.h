#pragma once
#include "playerbot/AiFactory.h"

namespace ai
{
    inline bool ClassicMageFrostPrimary(PlayerbotAI* ai)
    {
#ifdef MANGOSBOT_ZERO
        return ai->GetBot()->HasSpell(12042) && !ai->IsInPvp() &&
            AiFactory::GetPlayerSpecTabs(ai->GetBot())[2]>=15;
#else
        return false;
#endif
    }

    inline const char* MagePrimaryDamageSpell(PlayerbotAI* ai)
    {
        if (ClassicMageFrostPrimary(ai)) return "frostbolt";
        if (ai->HasStrategy("fire raid",BotState::BOT_STATE_COMBAT)) return "fireball";
        if (ai->HasStrategy("arcane raid",BotState::BOT_STATE_COMBAT)) return "arcane missiles";
        return "frostbolt";
    }
}
