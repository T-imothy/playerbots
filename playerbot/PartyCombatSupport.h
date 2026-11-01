#pragma once

class Player;
class PlayerbotAI;

namespace ai
{
    // Same-instance, nearby combat only; never follows a remote party member.
    Player* GetPartyCombatAnchor(PlayerbotAI* ai);
    // Keep raid healers/pet casters in the same combat state as a nearby,
    // natively engaged teammate even without a personal hostile target.
    bool HasClassicRaidPartyCombat(PlayerbotAI* ai);
    bool NeedsPartyCombatSupport(PlayerbotAI* ai);
}
