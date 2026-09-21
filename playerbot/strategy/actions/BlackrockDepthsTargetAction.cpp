#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/MeleeCombatPolicy.h"
#include "playerbot/strategy/values/PossibleTargetsValue.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"

using namespace ai;

namespace
{
    // Entries verified against Classic ACID and the native BRD scripts.
    // Smaller ranks are more urgent. Unlisted enemies still participate,
    // including arena bosses, the Seven, bar fights and optional encounters.
    unsigned BrdTargetRank(uint32 entry)
    {
        switch (entry)
        {
            case 8894: return 0; // Anvilrage Medic; also Angerforge reinforcements.
            case 8895: case 8898: return 1; // Officer / Marshal: Holy Light.
            case 8897: return 2; // Doomforge Craftsman: Rebuild repairs constructs.
            case 8911: case 8900: return 3; // Fireguard Destroyer / Arcanasmith: AoE.
            case 8913: case 8915: // Twilight Emissary / Ambassador.
            case 8909: case 8910: // Fireguards.
            case 8904: case 8920: return 4; // Senator / Weapon Technician.
            case 8901: return 5; // Angerforge's Anvilrage Reservists.
            default: return 6;
        }
    }
}

Unit* DungeonAddTargetAction::GetBlackrockDepthsTarget()
{
    if (bot->GetMapId() != 230 || !bot->GetGroup() || !bot->IsInWorld() ||
        !bot->IsAlive() || !bot->IsInCombat() || bot->IsBeingTeleported() ||
        bot->HasCharmer() || ai->IsRealPlayer() || ai->IsHeal(bot) || ai->IsTank(bot))
        return nullptr;

    Unit* selected = nullptr;
    unsigned selectedRank = 100;
    bool emperorEngaged = false;
    const auto attackers = AI_VALUE(std::list<ObjectGuid>, "attackers");
    auto groupMember = [this](Unit* unit)
    {
        if (!unit) return false;
        if (!unit->IsPlayer()) unit = ai->GetUnit(unit->GetMasterGuid());
        return unit && unit->IsPlayer() && unit->IsInWorld() && bot->IsInMap(unit) &&
            static_cast<Player*>(unit)->GetGroup() == bot->GetGroup();
    };
    auto engaged = [&groupMember](Unit* unit)
    {
        if (groupMember(unit->GetVictim())) return true;
        // A healer can have no current victim yet still have this party on
        // its threat list. Do not infer engagement merely from proximity.
        for (auto* ref : unit->getThreatManager().getThreatList())
            if (ref && groupMember(ref->getTarget())) return true;
        return false;
    };
    for (const auto& guid : attackers)
    {
        Unit* unit = ai->GetUnit(guid);
        if (unit && unit->GetEntry() == 9019 && unit->IsInWorld() && unit->IsAlive() &&
            bot->IsInMap(unit) && unit->IsInCombat() && engaged(unit))
            emperorEngaged = true;
    }
    for (const auto& guid : attackers)
    {
        Unit* unit = ai->GetUnit(guid);
        if (!unit || !unit->IsCreature() || !unit->IsInWorld() || !unit->IsAlive() || !bot->IsInMap(unit) ||
            !unit->IsInCombat() || unit->HasCharmer() || !engaged(unit) ||
            std::fabs(unit->GetPositionZ() - bot->GetPositionZ()) > 8.0f ||
            !PossibleTargetsValue::IsValid(unit, bot, false) ||
            !PossibleAttackTargetsValue::IsPossibleTarget(unit, bot, sPlayerbotAIConfig.sightDistance, false) ||
            PossibleAttackTargetsValue::HasBreakableCC(unit, bot) ||
            PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot) ||
            MeleeCcCheck(ai).Protected(unit)) continue;
        // NPC Divine Shield: spend the immunity window on another engaged
        // target. Do not remove the aura or alter the NPC's spell/cooldown.
        if (unit->HasAura(13874)) continue;
        // Prefer the Emperor while both are hostile; explicit player marks
        // are handled before this policy. This is not automatic quest rescue
        // and does not make Moira immune to incidental area damage.
        if (emperorEngaged && unit->GetEntry() == 8929) continue;

        const unsigned rank = BrdTargetRank(unit->GetEntry());
        // Lowest health within the same role finishes enemies; GUID ties
        // are deterministic across bots instead of depending on distance.
        if (!selected || rank < selectedRank ||
            (rank == selectedRank && (unit->GetHealth() < selected->GetHealth() ||
                (unit->GetHealth() == selected->GetHealth() &&
                    unit->GetObjectGuid() < selected->GetObjectGuid()))))
        {
            selected = unit;
            selectedRank = rank;
        }
    }
    return selected;
}
