
#include "playerbot/playerbot.h"
#include "CcTargetValue.h"
#include "playerbot/PlayerbotAIConfig.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/strategy/Action.h"
#include "playerbot/strategy/values/RtiTargetValue.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;

namespace
{
    bool GarrBanishAssignment(PlayerbotAI* ai, const std::string& spell, Unit*& result)
    {
        Player* bot = ai->GetBot();
        if (spell != "banish" || bot->GetMapId() != 409 || !bot->GetGroup() ||
            !bot->IsInCombat() || bot->HasCharmer() || ai->IsRealPlayer()) return false;
        AiObjectContext* context = ai->GetAiObjectContext();
        // An explicit CC mark retains the usual player-directed selection.
        if (AI_VALUE(Unit*, "rti cc target")) return false;
        const auto possible = AI_VALUE(std::list<ObjectGuid>, "possible targets no los");
        Unit* boss = nullptr;
        for (const auto& guid : possible)
        {
            Unit* unit = ai->GetUnit(guid);
            if (!unit || unit->GetEntry() != 12057 || !unit->IsInWorld() || !unit->IsAlive() ||
                !bot->IsInMap(unit) || !unit->IsInCombat() || unit->HasCharmer()) continue;
            if (boss && boss != unit) return false;
            boss = unit;
        }
        if (!boss) return false;
        std::vector<Player*> warlocks;
        for (GroupReference* ref = bot->GetGroup()->GetFirstMember(); ref; ref = ref->next())
        {
            Player* member = ref->getSource();
            if (!member || !member->IsInWorld() || !member->IsAlive() || !bot->IsInMap(member) ||
                member->GetGroup() != bot->GetGroup() || member->IsBeingTeleported() || member->HasCharmer() ||
                member->getClass() != CLASS_WARLOCK || (!member->HasSpell(710) && !member->HasSpell(18647)) ||
                member->GetDistance(boss) > sPlayerbotAIConfig.sightDistance || !member->GetPlayerbotAI() ||
                member->GetPlayerbotAI()->IsRealPlayer() ||
                !member->GetPlayerbotAI()->HasStrategy("cc", BotState::BOT_STATE_COMBAT)) continue;
            warlocks.push_back(member);
        }
        std::sort(warlocks.begin(), warlocks.end(), [](Player* a, Player* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        const auto own = std::find(warlocks.begin(), warlocks.end(), bot);
        if (own == warlocks.end()) return true;
        std::vector<Unit*> adds;
        const ObjectGuid skull = bot->GetGroup()->GetTargetIcon(7);
        // Every participant needs the same boss-centred view. Per-bot sight
        // lists can contain different subsets and assign two locks one add.
        std::list<Unit*> firesworn;
        MaNGOS::AllCreaturesOfEntryInRangeCheck check(boss, 12099, 100.0f);
        MaNGOS::UnitListSearcher<MaNGOS::AllCreaturesOfEntryInRangeCheck> searcher(firesworn, check);
        Cell::VisitAllObjects(boss, searcher, 100.0f);
        for (Unit* add : firesworn)
        {
            if (!add || add->GetEntry() != 12099 || !add->IsInWorld() || !add->IsAlive() ||
                !bot->IsInMap(add) || !add->IsInCombat() || add->HasCharmer() ||
                add->GetObjectGuid() == skull || sServerFacade.IsFriendlyTo(bot, add) ||
                add->GetDistance(boss) > 100.0f) continue;
            // Keep bot-owned banishes in the ordering so a successful cast
            // cannot shift every other warlock onto a different add.
            if (add->HasAura(710) || add->HasAura(18647))
            {
                bool owned = false;
                for (Player* member : warlocks)
                    if (add->GetSpellAuraHolder(710, member->GetObjectGuid()) ||
                        add->GetSpellAuraHolder(18647, member->GetObjectGuid())) { owned = true; break; }
                if (!owned) continue; // Human CC is not reassigned.
            }
            adds.push_back(add);
        }
        std::sort(adds.begin(), adds.end(), [](Unit* a, Unit* b) { return a->GetObjectGuid() < b->GetObjectGuid(); });
        const size_t slot = std::distance(warlocks.begin(), own);
        if (slot < adds.size() && !adds[slot]->HasAura(710) && !adds[slot]->HasAura(18647) &&
            ai->CanCastSpell(spell, adds[slot], 0, nullptr, false, true)) result = adds[slot];
        return true;
    }
}

class FindTargetForCcStrategy : public FindTargetStrategy
{
public:
    FindTargetForCcStrategy(PlayerbotAI* ai, std::string spell) : FindTargetStrategy(ai)
    {
        this->spell = spell;
        maxDistance = sPlayerbotAIConfig.sightDistance;
    }

public:
    virtual void CheckAttacker(Unit* creature, ThreatManager* threatManager)
    {
        Player* bot = ai->GetBot();
        if (!bot || !bot->IsInWorld() || bot->IsBeingTeleported() || !bot->IsAlive() ||
            !creature || !creature->IsInWorld() || !creature->IsAlive() || !bot->IsInMap(creature))
            return;

        AiObjectContext* context = ai->GetAiObjectContext();

        Unit* markedTarget = AI_VALUE(Unit*, "rti cc target");
        if (markedTarget && markedTarget->GetObjectGuid() == creature->GetObjectGuid())
        {
            // The mark overrides automatic CC heuristics, not spellbook,
            // resource, cooldown or native immunity rules. Normal reach-spell
            // handling may close distance/LOS before the eventual cast check.
            if (ai->CanCastSpell(spell, creature, 0, nullptr, true, true))
                result = creature;
            return;
        }

        if (AI_VALUE(Unit*,"current target") == creature)
            return;

        if (AI_VALUE(Unit*,"rti target") == creature)
            return;

        uint8 health = creature->GetHealthPercent();
        if (health < sPlayerbotAIConfig.mediumHealth)
            return;

        float minDistance = ai->GetRange("spell");
        Group* group = bot->GetGroup();
        if (!group)
            return;

        if (AI_VALUE(uint8,"aoe count") > 2)
        {
            WorldLocation aoe = AI_VALUE(WorldLocation,"aoe position");
            if (sServerFacade.IsDistanceLessOrEqualThan(sServerFacade.GetDistance2d(creature, aoe.coord_x, aoe.coord_y), sPlayerbotAIConfig.aoeRadius))
                return;
        }

        if (creature->HasAuraType(SPELL_AURA_PERIODIC_DAMAGE) && !(spell == "fear" || spell == "banish"))
            return;

        if (!ai->CanCastSpell(spell, creature, 0, nullptr, false, true))
            return;

        // If we have rti cc none but have cc strategy, then we'll cc something we're able to
        std::string rti = AI_VALUE(std::string, "rti cc");
        int index = RtiTargetValue::GetRtiIndex(rti);
        if (index == -1 && ai->HasStrategy("cc", BotState::BOT_STATE_COMBAT))
        {
            Group::MemberSlotList const& groupSlot = group->GetMemberSlots();
            for (Group::member_citerator itr = groupSlot.begin(); itr != groupSlot.end(); itr++)
            {
                Player *member = sObjectMgr.GetPlayer(itr->guid);
                if (!member || !member->IsInWorld() || !sServerFacade.IsAlive(member) ||
                    member->IsBeingTeleported() || member == bot || !bot->IsInMap(member))
                    continue;

                if (!ai->IsTank(member))
                    continue;

                float distance = sServerFacade.GetDistance2d(member, creature);
                if (distance < minDistance)
                    minDistance = distance;
            }

            if ((!result && !creature->IsPlayer()) || minDistance > maxDistance)
            {
                result = creature;
                maxDistance = minDistance;
            }
        }
    }

private:
    std::string spell;
    float maxDistance;
};

Unit* CcTargetValue::Calculate()
{
    if (!bot || !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported())
        return nullptr;

    std::list<ObjectGuid> possible = AI_VALUE(std::list<ObjectGuid>,"possible targets no los");

    for (std::list<ObjectGuid>::iterator i = possible.begin(); i != possible.end(); ++i)
    {
        ObjectGuid guid = *i;
        Unit* add = ai->GetUnit(guid);
        if (!add || !add->IsInWorld() || !add->IsAlive() || !bot->IsInMap(add))
            continue;

        if (ai->HasMyAura(qualifier, add))
            return NULL;

        if (qualifier == "polymorph")
        {
            if (ai->HasMyAura("polymorph: pig", add))
                return NULL;
            if (ai->HasMyAura("polymorph: turtle", add))
                return NULL;
        }
    }

    Unit* assigned = nullptr;
    if (GarrBanishAssignment(ai, qualifier, assigned)) return assigned;
    FindTargetForCcStrategy strategy(ai, qualifier);
    return FindTarget(&strategy);
}
