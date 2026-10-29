#pragma once

namespace ai
{
    // Generic target-dropping recovery belongs to autonomous outdoor bots.
    // Encounter, group, player-command, and active-cast recovery has its own
    // ownership and timing; a motionless actor there is not an abandoned fight.
    template<class AI>
    bool CanUseSoloMovementRecovery(AI* ai)
    {
        if (!ai || ai->IsRealPlayer() || ai->HasRealPlayerMaster())
            return false;
        auto* bot = ai->GetBot();
        return bot && bot->IsInWorld() && bot->IsAlive() &&
            !bot->IsBeingTeleported() && !bot->HasCharmer() &&
            !bot->GetGroup() && !bot->InBattleGround() &&
            !bot->GetMap()->IsDungeon() && !bot->GetMap()->IsRaid() &&
            ai->CanMove() && !bot->IsNonMeleeSpellCasted(false, false, true);
    }
}
