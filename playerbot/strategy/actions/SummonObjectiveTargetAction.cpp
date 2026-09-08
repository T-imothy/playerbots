#include "playerbot/playerbot.h"
#include "DungeonActions.h"
#include "playerbot/strategy/AiObjectContext.h"
#include "playerbot/strategy/values/PossibleTargetsValue.h"
#include "playerbot/strategy/values/PossibleAttackTargetsValue.h"

using namespace ai;

Unit* DungeonAddTargetAction::GetSummonObjectiveTarget()
{
    uint32 bossEntry = 0, addEntry = 0, phaseAura = 0;
    uint32 playerSummonSpell = 0;
    bool staticBeacon = false;
    switch (bot->GetMapId())
    {
        case 230: bossEntry = 9156; addEntry = 9178; break; // Flamelash's approaching Burning Spirits.
        case 509: bossEntry = 15340; addEntry = 15527; break;
        case 531: bossEntry = 15299; addEntry = 15667; break;
#ifndef MANGOSBOT_ZERO
        case 548: bossEntry = 21212; phaseAura = 38112; break; // Vashj's shield-phase waves.
        case 553: bossEntry = 17977; addEntry = 19949; break; // Warp Splinter's saplings.
        case 556: bossEntry = 18472; break; // Syth's four native elementals.
        case 557: bossEntry = 18344; addEntry = 18431; staticBeacon = true; break;
        case 558: bossEntry = 18373; break; // Maladaar's player souls and boss-owned avatar.
#ifdef MANGOSBOT_TWO
        case 576: bossEntry = 26731; break; // Telestra's split or heroic Ormorok's Tanglers.
        case 608: bossEntry = 29313; addEntry = 29321; break; // Ichoron globules, including after his first merge.
        case 619: bossEntry = 29310; addEntry = 30385; phaseAura = 56100; break;
        case 632: bossEntry = 36497; addEntry = 36535; playerSummonSpell = 68846; break;
        case 650: bossEntry = 34928; phaseAura = 66515; break; // Paletress's shield ends when her memory dies.
#endif
#endif
        default: return nullptr;
    }
    if (!bot->GetGroup() || !bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() ||
        bot->HasCharmer() || bot->IsBeingTeleported()) return nullptr;
    auto live = [this](Unit* unit) {
        return unit && unit->IsInWorld() && unit->IsAlive() && bot->IsInMap(unit) && !unit->HasCharmer();
    };
    auto member = [this, &live](Unit* unit) {
        return live(unit) && unit->IsPlayer() && !static_cast<Player*>(unit)->IsBeingTeleported() &&
            static_cast<Player*>(unit)->GetGroup() == bot->GetGroup();
    };
    // Include the unattackable boss during a split/sacrifice. Only objectives
    // selected below are admitted to the native attackability checks.
    const auto nearby = AI_VALUE2(std::list<ObjectGuid>, "possible targets", "100:1");
    Unit* boss = nullptr;
    for (const auto& guid : nearby)
    {
        Unit* candidate = ai->GetUnit(guid);
        if (!live(candidate)) continue;
        bool matchingBoss = candidate->GetEntry() == bossEntry ||
            (bot->GetMapId() == 531 && candidate->GetEntry() == 15510);
#ifdef MANGOSBOT_TWO
        if (bot->GetMapId() == 576)
            matchingBoss = (candidate->GetEntry() == 26731 && candidate->HasAura(47710)) ||
                (candidate->GetEntry() == 26794 && !bot->GetMap()->IsRegularDifficulty());
#endif
        if (!matchingBoss || !candidate->IsInCombat() ||
            candidate->GetVictim() == bot || bot->GetDistance(candidate) > 100 ||
            (phaseAura && !candidate->HasAura(phaseAura))) continue;
        if (boss && boss != candidate) return nullptr;
        boss = candidate;
    }
    if (!boss) return nullptr;
    if (bot->GetMapId() == 531 && boss->GetEntry() == 15510) addEntry = 15630; // Enraging Spawn of Fankriss.
    Unit* selected = nullptr;
    Unit* current = AI_VALUE(Unit*, "current target");
    for (const auto& guid : nearby)
    {
        Unit* add = ai->GetUnit(guid);
        if (!live(add)) continue;
        bool entryMatches = add->GetEntry() == addEntry;
#ifndef MANGOSBOT_ZERO
        if (bot->GetMapId() == 548)
            entryMatches = add->GetEntry() == 22009 || add->GetEntry() == 21958 ||
                add->GetEntry() == 22055 || (add->GetEntry() == 22056 && ai->IsRanged(bot));
        if (bot->GetMapId() == 556)
            entryMatches = add->GetEntry() >= 19203 && add->GetEntry() <= 19206;
        if (bot->GetMapId() == 558)
        {
            entryMatches = add->GetEntry() == 18441 || add->GetEntry() == 18478;
            playerSummonSpell = add->GetEntry() == 18441 ? 32360 : 0;
        }
#endif
#ifdef MANGOSBOT_TWO
        if (bot->GetMapId() == 576)
            entryMatches = boss->GetEntry() == 26731 ? add->GetEntry() >= 26928 && add->GetEntry() <= 26930 :
                add->GetEntry() == 32665 && add->HasAura(61555);
        if (bot->GetMapId() == 650)
        {
            // Exact templates from the native 25-spell Summon Memory table.
            static const uint32 memories[] = {34942, 35028, 35029, 35030, 35031, 35032, 35033, 35034,
                35036, 35037, 35038, 35039, 35040, 35041, 35042, 35043, 35044, 35045, 35046,
                35047, 35048, 35049, 35050, 35051, 35052};
            entryMatches = std::find(std::begin(memories), std::end(memories), add->GetEntry()) != std::end(memories);
        }
#endif
        if (!entryMatches || add->GetDistance(boss) > 100 ||
            !PossibleTargetsValue::IsValid(add, bot, false) ||
            !PossibleAttackTargetsValue::IsPossibleTarget(add, bot, sPlayerbotAIConfig.sightDistance, false)) continue;
        Unit* source = ai->GetUnit(add->GetSpawnerGuid());
        if (playerSummonSpell)
        {
            // Corrupt Soul expires before the player casts Draw Corrupted Soul.
            // Verify its actual summon spell instead of requiring the expired aura.
            if (!member(source) || add->GetUInt32Value(UNIT_CREATED_BY_SPELL) != playerSummonSpell) continue;
        }
        else if (source != boss)
        {
            // Shaffar also starts with static beacons. Only ones already engaged
            // by this group qualify; a nearby idle beacon is never permission to pull.
            if (!staticBeacon || !add->GetSpawnerGuid().IsEmpty() || !add->IsInCombat() ||
                !member(add->GetVictim()) || !member(boss->GetVictim())) continue;
        }
        if (addEntry == 30385 && add->HasAura(56102)) continue; // Unchosen volunteer.
        if (bot->GetMapId() == 548)
        {
            auto rank = [](Unit* unit) {
                return unit->GetEntry() == 22009 ? 0 : unit->GetEntry() == 21958 ? 1 :
                    unit->GetEntry() == 22056 ? 2 : 3;
            };
            // Tainted elementals disappear quickly and supply the required key.
            // Enchanted elementals closest to the boss are next to empower her.
            if (!selected || rank(add) < rank(selected) ||
                (rank(add) == rank(selected) && (add->GetEntry() == 21958 ?
                    add->GetDistance(boss) < selected->GetDistance(boss) :
                    add == current || (selected != current && bot->GetDistance(add) < bot->GetDistance(selected)))))
                selected = add;
            continue;
        }
        if (bot->GetMapId() == 230)
        {
            // A spirit that reaches Flamelash sacrifices itself to strengthen him.
            // Stop the nearest one first, even when another spirit is selected.
            if (!selected || add->GetDistance(boss) < selected->GetDistance(boss) ||
                (add->GetDistance(boss) == selected->GetDistance(boss) && add == current))
                selected = add;
            continue;
        }
        if (!selected || add == current || (selected != current && bot->GetDistance(add) < bot->GetDistance(selected)))
            selected = add;
    }
    return selected;
}
