#include "playerbot/playerbot.h"
#include "HazardsValue.h"
#include "EncounterPositionValue.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/strategy/ZulGurubEncounter.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;

void ai::AppendZulGurubActorHazards(PlayerbotAI* ai, std::list<HazardPosition>& hazards)
{
    Player* bot = ai->GetBot();
    if (!bot || bot->GetMapId() != 309 || !bot->IsInWorld() || !bot->IsAlive() ||
        !bot->GetGroup() || bot->IsBeingTeleported() || bot->HasCharmer() || ai->IsRealPlayer() ||
        !ai->HasStrategy("dungeon", BotState::BOT_STATE_COMBAT)) return;
    struct Rule { uint32 actor, owner, summon, aura, payload; };
    // Both are native creatures, not DynamicObjects. Spirit Burst procs from
    // the spirit's melee around its victim; the rooted Infernal pulses Immolation.
    static const Rule rules[] = {
        {15009, 11831, 24052, 24051, 24050},
#ifdef MANGOSBOT_ZERO
        {89, 14883, 24670, 19483, 20153}
#else
        // Later-era24670 summons22203, not Classic89. Their current native
        // template has no Immolation: do not fabricate a hazard without its aura.
        {22203, 14883, 24670, 19483, 20153}
#endif
    };
    for (const Rule& rule : rules)
    {
        std::list<Unit*> actors;
        MaNGOS::AllCreaturesOfEntryInRangeCheck check(bot, rule.actor, 60.0f);
        MaNGOS::UnitListSearcher<decltype(check)> searcher(actors, check);
        Cell::VisitAllObjects(bot, searcher, 60.0f);
        for (Unit* actor : actors)
        {
            if (!actor->IsInWorld() || !actor->IsAlive() || actor->HasCharmer() || !bot->IsInMap(actor) ||
                sServerFacade.IsFriendlyTo(bot, actor) || std::fabs(actor->GetPositionZ() - bot->GetPositionZ()) > 8 ||
                actor->GetUInt32Value(UNIT_CREATED_BY_SPELL) != rule.summon ||
                !actor->GetSpellAuraHolder(rule.aura, actor->GetObjectGuid())) continue;
            Unit* owner = ai->GetUnit(actor->GetSpawnerGuid());
            if (!owner || owner->GetTypeId() != TYPEID_UNIT || owner->GetEntry() != rule.owner ||
                !owner->IsInWorld() || !bot->IsInMap(owner) || owner->HasCharmer() || sServerFacade.IsFriendlyTo(bot, owner)) continue;
            // The Witch Doctor summons on death. Native group kill credit
            // preserves this hazard after combat ends without accepting an idle
            // unrelated pack or requiring the dead summoner to have a victim.
            const bool groupCorpse = !owner->IsAlive() && static_cast<Creature*>(owner)->GetGroupLootRecipient() == bot->GetGroup();
            if (!groupCorpse && !ZulGurubGroupEngaged(bot, owner) && !ZulGurubGroupEngaged(bot, actor)) continue;
            const float radius = NativeEncounterSpellRadius(rule.payload);
            if (!std::isfinite(radius) || radius <= 0 || radius > 35) continue;
            hazards.emplace_back(WorldPosition(actor), radius + 1.0f);
            if (rule.actor == 15009)
            {
                Unit* victim = actor->GetVictim();
                if (victim && victim->IsInWorld() && bot->IsInMap(victim) &&
                    actor->CanReachWithMeleeAttack(victim) &&
                    (ZulGurubGroupMember(bot, victim) || ZulGurubGroupMember(bot, victim->GetMaster())))
                    hazards.emplace_back(WorldPosition(victim), radius + 1.0f);
            }
        }
    }
}
