#pragma once
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"

namespace ai
{
    inline bool MoltenCoreImpAoeOpening(PlayerbotAI* ai)
    {
        Player* bot=ai->GetBot();
        if (!bot || !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() ||
            bot->HasCharmer() || bot->GetMapId()!=409 || !bot->IsInCombat() || ai->IsTank(bot)) return false;
        const time_t started=ai->GetCombatStartTime();
        if (started && time(0)-started>=10) return false;
        for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
        {
            Unit* imp=ai->GetUnit(guid);
            if (imp && imp->GetEntry()==11669 && imp->IsInWorld() && imp->IsAlive() &&
                imp->IsInCombat() && !imp->HasCharmer() && bot->IsInMap(imp)) return true;
        }
        return false;
    }

    inline Unit* MoltenCoreNukeTarget(PlayerbotAI* ai)
    {
        Player* bot = ai->GetBot();
        if (!bot || !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported() ||
            bot->HasCharmer() || bot->GetMapId() != 409 || !bot->IsInCombat()) return nullptr;
        Unit* selected = nullptr;
        Unit* marked = ai->GetUnit(ai->GetAiObjectContext()->GetValue<ObjectGuid>("rti target")->Get());
        for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible attack targets")->Get())
        {
            Unit* unit = ai->GetUnit(guid);
            if (!unit || !unit->IsInWorld() || !unit->IsAlive() || !bot->IsInMap(unit) ||
                !unit->IsInCombat() || (unit->GetEntry() != 11666 && unit->GetEntry() != 11667) ||
                !PossibleAttackTargetsValue::IsValid(unit, bot, sPlayerbotAIConfig.sightDistance, false, true) ||
                PossibleAttackTargetsValue::HasBreakableCC(unit, bot) ||
                PossibleAttackTargetsValue::HasUnBreakableCC(unit, bot)) continue;
            // Respect a skull on either priority mob, never on its accompanying elemental.
            if (unit == marked) return unit;
            if (!selected || unit->GetHealthPercent() < selected->GetHealthPercent() ||
                (unit->GetHealthPercent() == selected->GetHealthPercent() && unit->GetObjectGuid() < selected->GetObjectGuid()))
                selected = unit;
        }
        return selected;
    }

    inline bool MoltenCoreBossBurn(PlayerbotAI* ai)
    {
        Player* bot = ai->GetBot();
        if (!bot || !bot->IsInWorld() || bot->IsBeingTeleported() || bot->GetMapId() != 409) return false;
        for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
        {
            Unit* boss = ai->GetUnit(guid);
            if (boss && boss->IsInWorld() && boss->IsAlive() && boss->IsInCombat() && bot->IsInMap(boss) && (boss->GetEntry()==11988 || boss->GetEntry()==12018)) return true;
        }
        return false;
    }

    inline bool MoltenCoreBroadAoeSpell(const std::string& name)
    {
        for (const char* spell : {"blizzard", "flamestrike", "rain of fire", "hurricane", "volley",
            "death and decay", "mind sear", "seed of corruption", "living bomb", "starfall",
            "arcane explosion", "cone of cold", "dragon's breath", "blast wave", "hellfire",
            "shadowfury", "immolation aura", "shadowflame", "typhoon", "thunderstorm", "chain lightning",
            "whirlwind", "thunder clap", "consecration", "swipe", "divine storm", "fan of knives",
            "fire nova", "fire nova totem", "magma totem", "explosive trap"})
            if (name == spell) return true;
        return false; // Cleave, Blade Flurry, Multi-Shot and tank threat remain available.
    }

    inline bool MoltenCoreTrashSpellAllowed(PlayerbotAI* ai, const std::string& name)
    {
        // Majordomo requires single-target damage, including tank attacks:
        // neither cleave nor broad AoE may release another assigned sheep.
        Player* bot=ai->GetBot();
        if (MoltenCoreImpAoeOpening(ai) && (MoltenCoreBroadAoeSpell(name) ||
            name=="cleave" || name=="blade flurry" || name=="multi-shot")) return false;
        if (bot && bot->GetMapId()==409 && MoltenCoreBossBurn(ai))
            for (ObjectGuid guid : ai->GetAiObjectContext()->GetValue<std::list<ObjectGuid>>("possible targets no los")->Get())
            {
                Unit* boss=ai->GetUnit(guid);
                if (boss && boss->IsInWorld() && boss->IsAlive() && boss->IsInCombat() && bot->IsInMap(boss) && boss->GetEntry()==12018 &&
                    (MoltenCoreBroadAoeSpell(name) || name=="cleave" || name=="blade flurry" || name=="multi-shot"))
                    return false;
            }
        // Tanks retain native multi-target threat while DPS burn the dangerous pair.
        return !MoltenCoreBroadAoeSpell(name) || ai->IsTank(ai->GetBot()) || (!MoltenCoreNukeTarget(ai) && !MoltenCoreBossBurn(ai));
    }
}
