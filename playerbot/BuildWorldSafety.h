#pragma once

namespace living_build_safety
{
    // GetMap() asserts in CMaNGOS; it is not a nullable probe. A player
    // between maps can still receive an AI update from the previous map.
    template<class PlayerT> bool HasWorld(PlayerT* bot)
    {
        return bot && bot->IsInWorld() && !bot->IsBeingTeleported();
    }

    template<class PlayerT> bool CanReconcile(PlayerT* bot)
    {
        if (!HasWorld(bot) || bot->GetTransport() || bot->IsTaxiFlying() ||
            bot->IsInCombat() || !bot->IsAlive() || bot->InBattleGround() || bot->GetLevel() < 10)
            return false;
        return !bot->GetMap()->IsDungeon();
    }
}
