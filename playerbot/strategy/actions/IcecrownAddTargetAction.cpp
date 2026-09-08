#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleTargetsValue.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"

using namespace ai;

Unit* DungeonAddTargetAction::GetIcecrownAddTarget()
{
#ifdef MANGOSBOT_TWO
    if (bot->GetMapId() != 631 || !bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() ||
        !bot->GetGroup() || bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer()) return nullptr;
    // The dispatcher preserves tank/healer assignments and explicit targets.
    const bool ranged = ai->IsRanged(bot);
    const bool caster = ranged && bot->getClass() != CLASS_HUNTER;
    Unit* selected = nullptr;
    Unit* owner = nullptr;
    Unit* current = AI_VALUE(Unit*, "current target");
    unsigned selectedRank = 0;
    for (const auto& guid : AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1"))
    {
        Unit* add = ai->GetUnit(guid);
        if (!add || !add->IsInWorld() || !add->IsAlive() || !bot->IsInMap(add) || add->HasCharmer()) continue;
        uint32 bossEntry = 0;
        unsigned rank = 1;
        switch (add->GetEntry())
        {
            case 36980: // Release native Ice Tomb prisoners once air-phase cover is no longer required.
                bossEntry = 36853;
                rank = 0;
                break;
            case 38508: // Blood Beast: ranged DPS handle it without pulling melee off Saurfang.
                if (!ranged) continue;
                bossEntry = 37813;
                break;
            case 37890: case 37949: // Native Cult Fanatic / Adherent.
                bossEntry = 36855;
                break;
            case 38135: // Deformed Fanatic: its native transformation doubles damage.
                if (!ranged) continue;
                bossEntry = 36855;
                rank = 0;
                break;
            case 38136: case 38009: case 38010: // Empowered / reanimated cultists.
                bossEntry = 36855;
                rank = 0;
                break;
            default: continue;
        }
        Unit* boss = ai->GetUnit(add->GetSpawnerGuid());
        if (!boss || boss->GetEntry() != bossEntry || !boss->IsInWorld() || !boss->IsAlive() ||
            !boss->IsInCombat() || !bot->IsInMap(boss) || boss->HasCharmer() || boss->GetVictim() == bot ||
            bot->GetDistance(boss) > 100 || add->GetDistance(boss) > 100) continue;
        // Do not automatically destroy the raid's cover during takeoff, air
        // bombardment or landing. The native flight flag includes levitation.
        if (bossEntry == 36853 && boss->IsFlying()) continue;
        // Native self-applied Determination reduces its matching school by 99%.
        // Hunters use the physical assignment despite being ranged. Re-evaluate
        // the actual aura so a transformed target cannot retain a stale choice.
        if (bossEntry == 36855 && (caster ?
            add->GetSpellAuraHolder(71234, add->GetObjectGuid()) != nullptr :
            add->GetSpellAuraHolder(71235, add->GetObjectGuid()) != nullptr)) continue;
        if (!PossibleTargetsValue::IsValid(add, bot, false) ||
            !PossibleAttackTargetsValue::IsPossibleTarget(add, bot, sPlayerbotAIConfig.sightDistance, false)) continue;
        if (owner && owner != boss) return nullptr;
        owner = boss;
        if (!selected || rank < selectedRank || (rank == selectedRank &&
            (add == current || (selected != current && bot->GetDistance(add) < bot->GetDistance(selected)))))
        {
            selected = add;
            selectedRank = rank;
        }
    }
    return selected;
#else
    return nullptr;
#endif
}
