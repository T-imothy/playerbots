
#include "playerbot/playerbot.h"
#include "TrainerValues.h"
#include "SharedValueContext.h"
#include "playerbot/PlayerbotHelpMgr.h"
#include <memory>
#include <tuple>

using namespace ai;


trainableSpellMap* TrainableSpellMapValue::Calculate()
{
    auto spellMap = std::make_unique<trainableSpellMap>();
    using OfferKey = std::tuple<uint32, uint32, uint32, uint32, uint32, uint32, uint32, bool, uint32>;
    std::map<OfferKey, TrainerSpell const*> canonicalOffers;

    for (auto const& [id, nativeTemplate] : sObjectMgr.GetCreatureInfoMap())
    {
        CreatureInfo const* trainer = sCreatureStorage.LookupEntry<CreatureInfo>(id);
        if (!trainer || (!trainer->TrainerType && !trainer->TrainerClass))
            continue;
        TrainerType const type = static_cast<TrainerType>(trainer->TrainerType);
        TrainerSpellData const* entrySpells = sObjectMgr.GetNpcTrainerSpells(id);
        TrainerSpellData const* lists[] = {entrySpells,
            trainer->TrainerTemplateId ? sObjectMgr.GetNpcTrainerTemplateSpells(trainer->TrainerTemplateId) : nullptr};
        for (TrainerSpellData const* list : lists)
        {
            if (!list) continue;
            for (auto const& [spellId, offer] : list->spellList)
            {
                // Native HandleTrainerBuySpellOpcode gives entry-specific rows
                // precedence. Template IDs and creature IDs are distinct namespaces.
                if (list != entrySpells && entrySpells && entrySpells->Find(spellId))
                    continue;
                uint32 requirement = 0;
                if (type == TRAINER_TYPE_CLASS || type == TRAINER_TYPE_PETS)
                    requirement = trainer->TrainerClass;
                else if (type == TRAINER_TYPE_MOUNTS)
                    requirement = trainer->TrainerRace;
                else if (type == TRAINER_TYPE_TRADESKILLS)
                {
                    requirement = offer.reqSkill;
                    if (!requirement)
                    {
                        SpellEntry const* spell = sSpellTemplate.LookupEntry<SpellEntry>(offer.spell);
                        if (spell)
                            for (uint32 effect = 0; effect < 3; ++effect)
                                if ((spell->Effect[effect] == SPELL_EFFECT_SKILL ||
                                     spell->Effect[effect] == SPELL_EFFECT_SKILL_STEP) && spell->EffectMiscValue[effect] > 0)
                                {
                                    requirement = spell->EffectMiscValue[effect];
                                    break;
                                }
                    }
                }
                OfferKey key{uint32(type), requirement, offer.spell, offer.spellCost,
                    offer.reqSkill, offer.reqSkillValue, offer.reqLevel, offer.isProvidedReqLevel, offer.conditionId};
                TrainerSpell const* canonical = canonicalOffers.emplace(key, &offer).first->second;
                auto& trainers = (*spellMap)[type][requirement][canonical];
                if (std::find(trainers.begin(), trainers.end(), trainer->Entry) == trainers.end())
                    trainers.push_back(trainer->Entry);
            }
        }
    }
    return spellMap.release();
}

std::vector<TrainerSpell const*> TrainableSpellsValue::Calculate()
{
    std::vector<TrainerSpell const*> trainableSpells;

    int8 qualifierType = getQualifier().empty() ? -1 : stoi(getQualifier());

    trainableSpellMap* spellMap = GAI_VALUE(trainableSpellMap*, "trainable spell map");

    for (auto& [trainerType, spellReqList] : *spellMap)
    {
        if (qualifierType >= 0 && trainerType != qualifierType)
            continue;

        for (auto& [requirement, trainerSpellList] : spellReqList)
        {
            if (trainerType == TRAINER_TYPE_CLASS && requirement != bot->getClass())
                continue;
            if (trainerType == TRAINER_TYPE_MOUNTS && requirement != bot->getRace())
                continue;

            for (auto& [trainerSpell, trainers] : trainerSpellList)
            {
                uint32 reqLevel = 0;

                reqLevel = trainerSpell->isProvidedReqLevel ? trainerSpell->reqLevel : std::max(reqLevel, trainerSpell->reqLevel);
                TrainerSpellState state = bot->GetTrainerSpellState(trainerSpell, reqLevel);
                if (state != TRAINER_SPELL_GREEN)
                    continue;

                //Skip initial profession training.
#ifdef MANGOSBOT_ZERO
                if (bot->GetLevel() < 10 && sSpellMgr.IsProfessionSpell(trainerSpell->learnedSpell) && sSpellMgr.GetSpellRank(trainerSpell->learnedSpell) == 1)
#else
                if (bot->GetLevel() < 10 && sSpellMgr.IsProfessionSpell(trainerSpell->learnedSpell[0]) && sSpellMgr.GetSpellRank(trainerSpell->learnedSpell[0]) == 1)
#endif
                    continue;

                trainableSpells.push_back(trainerSpell);
            }
        }
    }   

    return trainableSpells;
}

std::string TrainableSpellsValue::Format()
{
    std::vector<std::string> vec;  
    for (auto t : value) {
        SpellEntry const* spell = sServerFacade.LookupSpellInfo(t->spell);
        if (!spell)
            continue;
        vec.push_back(chat->formatSpell(spell));
    } 
    
    return sPlayerbotHelpMgr.makeList(vec, "[<part>]");
}

std::vector<int32> AvailableTrainersValue::Calculate()
{
    std::vector<TrainerSpell const*> trainableSpells = AI_VALUE2(std::vector<TrainerSpell const*>, "trainable spells", getQualifier());;
    std::vector<int32> retTrainers;

    int8 qualifierType = getQualifier().empty() ? -1 : stoi(getQualifier());

    trainableSpellMap* spellMap = GAI_VALUE(trainableSpellMap*, "trainable spell map");

    for (auto& [trainerType, spellReqList] : *spellMap)
    {
        if (qualifierType >= 0 && trainerType != qualifierType)
            continue;

        for (auto& [requirement, trainerSpellList] : spellReqList)
        {
            if (trainerType == TRAINER_TYPE_CLASS && requirement != bot->getClass())
                continue;
            if (trainerType == TRAINER_TYPE_MOUNTS && requirement != bot->getRace())
                continue;

            for (auto& [trainerSpell, trainers] : trainerSpellList)
            {
                if (std::find(trainableSpells.begin(), trainableSpells.end(), trainerSpell) == trainableSpells.end())
                    continue;

                for (auto& trainer : trainers)
                {
                    if(std::find(retTrainers.begin(), retTrainers.end(), trainer) == retTrainers.end())
                        retTrainers.push_back(trainer);
                }
            }
        }
    }

    return retTrainers;
}

uint32 TrainCostValue::Calculate()
{
    uint32 TotalCost = 0;

    for (auto& spells : AI_VALUE2(std::vector<TrainerSpell const*>, "trainable spells", getQualifier()))
        TotalCost += spells->spellCost;
   
    return TotalCost;
}
