#include "playerbot/playerbot.h"
#include "HazardsValue.h"
#include "EncounterPositionValue.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;

void ai::AppendNativeEncounterActorHazards(PlayerbotAI* ai, std::list<HazardPosition>& hazards)
{
#ifndef MANGOSBOT_ZERO
    Player* bot = ai->GetBot();
    const uint32 map = bot->GetMapId();
    bool supported = map == 534 || map == 546 || map == 564 || map == 568;
#ifdef MANGOSBOT_TWO
    supported = supported || map == 603 || map == 631 || map == 632;
#endif
    if (!supported || !bot->IsInWorld() || !bot->IsAlive() || !bot->IsInCombat() ||
        !bot->GetGroup() || bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() ||
        !ai->HasStrategy("dungeon", BotState::BOT_STATE_COMBAT)) return;
    struct Rule
    {
        uint32 map, boss, actor, aura, payload;
        float clearance;
        uint32 playerSummonSpell = 0;
    };
    // Only native, harmful actor auras belong here. Passive hazards do not
    // necessarily enter combat; the live owner's encounter supplies that gate.
    static const Rule rules[] = {
        {534, 17968, 18095, 31945, 31943, 2.0f}, // Archimonde's moving Doomfire, with native trail damage radius.
        {546, 17770, 17990, 31690, 34168, 1.0f, 31692}, // Player-summoned mushroom, avoid its upcoming Spore Cloud.
        {568, 23578, 23920, 42629, 42630, 1.0f}, // Armed Jan'alai bomb; aura removed by native explosion.
        {568, 23863, 24136, 43120, 43121, 4.0f}, // Moving Feather Vortex, damage and knockback.
        {568, 23863, 24187, 43218, 43217, 1.0f}, // Zul'jin's Column of Fire.
        {564, 22898, 23085, 42055, 42052, 1.0f}, // Supremus Volcano, including active phase carryover.
        {564, 22898, 23095, 40980, 40253, 2.0f}, // Moving Molten Flame; native dynamic trails remain separate.
#ifdef MANGOSBOT_TWO
        {603, 33186, 34188, 64709, 64709, 1.0f}, // Razorscale's actual normal/heroic self aura.
        {603, 33186, 34188, 64734, 64734, 1.0f},
        {603, 32930, 33632, 63347, 63346, 4.0f, 63343}, // Kologarn's player-summoned left/right eyes.
        {603, 32930, 33632, 63977, 63976, 4.0f, 63343},
        {603, 32930, 33802, 63347, 63346, 4.0f, 63701},
        {603, 32930, 33802, 63977, 63976, 4.0f, 63701},
        {631, 36612, 36672, 69145, 69146, 2.0f}, // Marrowgar's moving Coldflame source.
        {631, 37955, 38163, 71267, 71268, 1.0f, 71266}, // Player-dropped Swarming Shadows, native spawn aura.
        {632, 36502, 36536, 68854, 68863, 1.0f}, // Well of Souls; normal/heroic payloads share the native radius.
#endif
    };
    struct ActorCheck
    {
        Player* bot;
        const Rule* begin;
        const Rule* end;
        Player const& GetFocusObject() const { return *bot; }
        bool operator()(Unit* unit) const
        {
            if (bot->GetDistance(unit) > 100) return false;
            for (auto row = begin; row != end; ++row)
                if (row->map == bot->GetMapId() && row->actor == unit->GetEntry()) return true;
            return false;
        }
    } check{bot, std::begin(rules), std::end(rules)};
    std::list<Unit*> actors;
    MaNGOS::UnitListSearcher<ActorCheck> searcher(actors, check);
    Cell::VisitAllObjects(bot, searcher, 100.0f);
    std::map<uint32, Unit*> encounterOwners;
    for (Unit* actor : actors)
    {
        if (!actor->IsInWorld() || !actor->IsAlive() || actor->HasCharmer() || !bot->IsInMap(actor) ||
            std::fabs(actor->GetPositionZ() - bot->GetPositionZ()) > 8) continue;
        for (const Rule& rule : rules)
        {
            if (rule.map != map || rule.actor != actor->GetEntry() ||
                !actor->GetSpellAuraHolder(rule.aura, actor->GetObjectGuid())) continue;
            Unit* boss = nullptr;
            if (rule.playerSummonSpell)
            {
                // Force-cast summons belong to the selected player. Keep the
                // exact native summon and group GUID checks even after that
                // player dies; the eye can remain alive for its native duration.
                if (actor->GetUInt32Value(UNIT_CREATED_BY_SPELL) != rule.playerSummonSpell ||
                    !bot->GetGroup()->IsMember(actor->GetSpawnerGuid())) continue;
                auto found = encounterOwners.find(rule.boss);
                if (found == encounterOwners.end())
                {
                    std::list<Unit*> owners;
                    MaNGOS::AllCreaturesOfEntryInRangeCheck ownerCheck(bot, rule.boss, 100.0f);
                    MaNGOS::UnitListSearcher<decltype(ownerCheck)> ownerSearch(owners, ownerCheck);
                    Cell::VisitAllObjects(bot, ownerSearch, 100.0f);
                    for (Unit* owner : owners)
                    {
                        if (!owner->IsInWorld() || !owner->IsAlive() || !owner->IsInCombat() ||
                            owner->HasCharmer() || !bot->IsInMap(owner)) continue;
                        if (boss) { boss = nullptr; break; }
                        boss = owner;
                    }
                    encounterOwners.emplace(rule.boss, boss);
                }
                else boss = found->second;
            }
            else boss = ai->GetUnit(actor->GetSpawnerGuid());
            if (!boss || boss->GetEntry() != rule.boss || !boss->IsInWorld() || !boss->IsAlive() ||
                !boss->IsInCombat() || boss->HasCharmer() || !bot->IsInMap(boss)) continue;
            const float radius = NativeEncounterSpellRadius(rule.payload);
            if (!std::isfinite(radius) || radius <= 0 || radius > 35) continue;
            hazards.emplace_back(WorldPosition(actor), radius + rule.clearance);
            break;
        }
    }
#endif
}
