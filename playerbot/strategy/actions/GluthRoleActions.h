#pragma once

class PlayerbotAI;
class Player;
class Unit;
namespace ai
{
    Player* GluthKiter(PlayerbotAI* ai, Unit* boss);
    bool GluthTankRelief(PlayerbotAI* ai, Unit* boss);
}
