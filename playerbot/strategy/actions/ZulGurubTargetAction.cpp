#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleTargetsValue.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"

using namespace ai;

Unit* DungeonAddTargetAction::GetZulGurubTarget()
{
    if (bot->GetMapId() != 309 || !bot->GetGroup() || !bot->IsInWorld() || !bot->IsAlive() ||
        !bot->IsInCombat() || bot->HasCharmer() || bot->IsBeingTeleported()) return nullptr;
    auto live = [this](Unit* unit) {
        return unit && unit->IsInWorld() && unit->IsAlive() && bot->IsInMap(unit) && !unit->HasCharmer();
    };
    auto member = [this, &live](Unit* unit) {
        return live(unit) && unit->IsPlayer() && !static_cast<Player*>(unit)->IsBeingTeleported() &&
            static_cast<Player*>(unit)->GetGroup() == bot->GetGroup();
    };
    const auto nearby = AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1");
    Unit* selected = nullptr;
    unsigned selectedRank = 0;
    Unit* current = ai->GetUnit(AI_VALUE(ObjectGuid, "current target"));
    for (const auto& guid : nearby)
    {
        Unit* add = ai->GetUnit(guid);
        if (!live(add)) continue;
        uint32 bossEntry = 0;
        switch (add->GetEntry())
        {
            case 14965: bossEntry = 14517; break; // Jeklik: bloodseeker bats, never flying bombers 14750.
            case 15041: bossEntry = 14510; break; // Mar'li: egg-spawned spiders.
            case 15101: bossEntry = 14515; break; // Arlokk: trigger-spawned panthers.
            case 14986: bossEntry = 11380; break; // Jin'do: only players with Delusions can see shades.
            case 15163: bossEntry = 15083; break; // Hazza'rah: lethal, low-health illusions.
            default: continue;
        }
        if (!PossibleTargetsValue::IsValid(add, bot, false) ||
            !PossibleAttackTargetsValue::IsPossibleTarget(add, bot, sPlayerbotAIConfig.sightDistance, false) ||
            PossibleAttackTargetsValue::HasBreakableCC(add, bot)) continue;
        if (add->GetEntry() == 14986 && (!bot->HasAura(24306) ||
            !add->IsVisibleForOrDetect(bot, bot->GetCamera().GetBody(), true))) continue;

        Unit* boss = nullptr;
        for (const auto& bossGuid : nearby)
        {
            Unit* candidate = ai->GetUnit(bossGuid);
            if (!live(candidate) || candidate->GetEntry() != bossEntry || !candidate->IsInCombat() ||
                candidate->GetVictim() == bot || candidate->GetDistance(add) > 100 ||
                (!member(candidate->GetVictim()) && !(bossEntry == 14515 && member(add->GetVictim())))) continue;
            // Arlokk resets threat and hides during vanish. Her summoned,
            // engaged panthers still need killing while she has no victim.
            if (boss && boss != candidate) return nullptr;
            boss = candidate;
        }
        if (!boss) continue;
        Unit* source = ai->GetUnit(add->GetSpawnerGuid());
        if (add->GetEntry() == 15041)
        {
            // Eggs are gameobjects, not boss-owned creatures. Require an
            // already engaged spider attacking this group instead of inventing
            // a Unit summoner or pulling an idle spider next to the encounter.
            if (!add->IsInCombat() || !member(add->GetVictim())) continue;
        }
        else if (add->GetEntry() == 15101)
        {
            if (!live(source) || source->GetEntry() != 15091 || source->GetDistance(boss) > 100 ||
                !add->IsInCombat() || !member(add->GetVictim())) continue;
        }
        else if (source != boss) continue;

        // Rescue the marked player first; otherwise finish the existing add
        // rather than oscillating as several equal-priority adds move around.
        const unsigned rank = add->GetEntry() == 15101 && member(add->GetVictim()) &&
            add->GetVictim()->GetSpellAuraHolder(24210, boss->GetObjectGuid()) ? 0 : 1;
        if (!selected || rank < selectedRank || (rank == selectedRank &&
            (add == current || (selected != current && bot->GetDistance(add) < bot->GetDistance(selected)))))
        {
            selected = add;
            selectedRank = rank;
        }
    }
    return selected;
}
