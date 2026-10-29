
#include "playerbot/playerbot.h"
#include "CcTargetValue.h"
#include "playerbot/PlayerbotAIConfig.h"
#include "playerbot/ServerFacade.h"
#include "playerbot/strategy/Action.h"
#include "playerbot/strategy/values/RtiTargetValue.h"
#include "playerbot/strategy/actions/MoltenCoreGarrActions.h"
#include "playerbot/strategy/actions/MoltenCoreLavaTrashActions.h"
#include "Grids/GridNotifiers.h"
#include "Grids/GridNotifiersImpl.h"
#include "Grids/CellImpl.h"

using namespace ai;

namespace
{
    bool GarrBanishAssignment(PlayerbotAI* ai, const std::string& spell, Unit*& result)
    {
        if (spell != "banish" || ai->GetBot()->GetMapId() != 409) return false;
        // MC banish is encounter-owned, including sequential post-Garr cleanup.
        // Never fall back to arbitrary trash CC or a second assignment scheme.
        result = GarrBanishTarget(ai);
        if (!result) result = LavaTrashBanishTarget(ai);
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

        Unit* markedTarget = ai->GetUnit(AI_VALUE(ObjectGuid, "rti cc target"));
        if (markedTarget && markedTarget->GetObjectGuid() == creature->GetObjectGuid())
        {
            // The mark overrides automatic CC heuristics, not spellbook,
            // resource, cooldown or native immunity rules. Normal reach-spell
            // handling may close distance/LOS before the eventual cast check.
            if (ai->CanCastSpell(spell, creature, 0, nullptr, true, true))
                result = creature;
            return;
        }

        if (AI_VALUE(ObjectGuid,"current target") == creature->GetObjectGuid())
            return;

        if (AI_VALUE(ObjectGuid,"rti target") == creature->GetObjectGuid())
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

                PlayerbotAI* memberAI = member->GetPlayerbotAI();
                ObjectGuid engagedTarget = memberAI
                    ? memberAI->GetAiObjectContext()->GetValue<ObjectGuid>("current target")->Get()
                    : member->GetSelectionGuid();
                if (engagedTarget == creature->GetObjectGuid())
                    return;

                if (!ai->IsTank(member))
                    continue;

                float distance = sServerFacade.GetDistance2d(member, creature);
                if (distance < minDistance)
                    minDistance = distance;
            }

            if (!result || minDistance > maxDistance)
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

ObjectGuid CcTargetValue::Calculate()
{
    if (!bot || !bot->IsInWorld() || !bot->IsAlive() || bot->IsBeingTeleported())
        return ObjectGuid();

    std::list<ObjectGuid> possible = AI_VALUE(std::list<ObjectGuid>,"possible targets no los");

    for (std::list<ObjectGuid>::iterator i = possible.begin(); i != possible.end(); ++i)
    {
        ObjectGuid guid = *i;
        Unit* add = ai->GetUnit(guid);
        if (!add || !add->IsInWorld() || !add->IsAlive() || !bot->IsInMap(add))
            continue;

        if (ai->HasMyAura(qualifier, add))
            return ObjectGuid();

        if (qualifier == "polymorph")
        {
            if (ai->HasMyAura("polymorph: pig", add))
                return ObjectGuid();
            if (ai->HasMyAura("polymorph: turtle", add))
                return ObjectGuid();
        }
    }

    Unit* assigned = nullptr;
    if (GarrBanishAssignment(ai, qualifier, assigned))
        return assigned ? assigned->GetObjectGuid() : ObjectGuid();
    FindTargetForCcStrategy strategy(ai, qualifier);
    Unit* target = FindTarget(&strategy);
    return target ? target->GetObjectGuid() : ObjectGuid();
}
