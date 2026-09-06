
#include "playerbot/playerbot.h"
#include "PartyMemberToDispel.h"

#include "playerbot/ServerFacade.h"
#include "playerbot/strategy/actions/EncounterSpellPolicy.h"
using namespace ai;

class PartyMemberToDispelPredicate : public FindPlayerPredicate, public PlayerbotAIAware
{
public:
    PartyMemberToDispelPredicate(PlayerbotAI* ai, uint32 dispelType, const SpellEntry* spell) :
        PlayerbotAIAware(ai), FindPlayerPredicate(), dispelType(dispelType), spell(spell) {}

public:
    virtual bool Check(Unit* unit) override
    {
        Pet* pet = dynamic_cast<Pet*>(unit);
        if (pet && (pet->getPetType() == MINI_PET || pet->getPetType() == SUMMON_PET))
            return false;

        return unit && sServerFacade.IsAlive(unit) && sServerFacade.GetDistance2d(ai->GetBot(), unit) <= ai->GetRange("spell") &&
            ai->HasAuraToDispel(unit, dispelType) && !ShouldAvoidEncounterDispel(ai, spell, unit);
    }

private:
    uint32 dispelType;
    const SpellEntry* spell;
};

Unit* PartyMemberToDispel::Calculate()
{
    const size_t separator = qualifier.find(',');
    uint32 dispelType = atoi(qualifier.substr(0, separator).c_str());
    const SpellEntry* spell = separator == std::string::npos ? nullptr :
        sServerFacade.LookupSpellInfo(AI_VALUE2(uint32, "spell id", qualifier.substr(separator + 1)));

    PartyMemberToDispelPredicate predicate(ai, dispelType, spell);
    return FindPartyMember(predicate);
}
