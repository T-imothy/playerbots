
#include "playerbot/playerbot.h"
#include "CcTargetValue.h"
#include "playerbot/PlayerbotAIConfig.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/strategy/Action.h"
#include "playerbot/strategy/values/RtiTargetValue.h"

using namespace ai;

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

    FindTargetForCcStrategy strategy(ai, qualifier);
    return FindTarget(&strategy);
}
