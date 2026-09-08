#pragma once

namespace ai
{
    inline bool CanManageBotCommands(PlayerbotAI* ai, Player* requester)
    {
        return requester && requester->isRealPlayer() &&
            ((ai->HasRealPlayerMaster() && ai->GetMaster() == requester) ||
                requester->GetSession()->GetSecurity() > SEC_PLAYER) &&
            ai->GetSecurity()->CheckLevelFor(PlayerbotSecurityLevel::PLAYERBOT_SECURITY_ALLOW_ALL, true, requester);
    }
}
