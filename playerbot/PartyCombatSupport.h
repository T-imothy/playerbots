#pragma once

class Player;
class PlayerbotAI;

namespace ai
{
    // Same-instance, nearby combat only; never follows a remote party member.
    Player* GetPartyCombatAnchor(PlayerbotAI* ai);
    bool NeedsPartyCombatSupport(PlayerbotAI* ai);
}
