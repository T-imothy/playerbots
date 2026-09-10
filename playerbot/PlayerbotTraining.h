#pragma once
#include <algorithm>

// Bot sessions alone receive the trainer subsidy. Human trainer handling stays
// in the core, with its normal prices and all normal spell prerequisites.
inline bool LivingWowFreeBotTraining(Player* player)
{
    return player && player->GetPlayerbotAI() && !player->isRealPlayer();
}

inline bool LivingWowCanTrainSpell(Player* bot, TrainerSpell const* spell, Unit* trainer = nullptr)
{
    if (!bot || !spell) return false;
    uint32 requiredLevel = 0;
    if (!bot->IsSpellFitByClassAndRace(spell->spell, &requiredLevel)) return false;
    requiredLevel = spell->isProvidedReqLevel ? spell->reqLevel : std::max(requiredLevel, spell->reqLevel);
    if (spell->conditionId && !sObjectMgr.IsConditionSatisfied(spell->conditionId,
        bot, bot->GetMap(), trainer ? trainer : bot, CONDITION_FROM_TRAINER)) return false;
    return bot->GetTrainerSpellState(spell, requiredLevel) == TRAINER_SPELL_GREEN;
}

inline bool LivingWowHasClassTraining(Player* bot, int32 entry)
{
    if (!bot || entry <= 0) return false;
    CreatureInfo const* trainer = sObjectMgr.GetCreatureTemplate(entry);
    if (!trainer || trainer->TrainerType != TRAINER_TYPE_CLASS ||
        trainer->TrainerClass != bot->getClass()) return false;
    TrainerSpellData const* lists[] = {
        sObjectMgr.GetNpcTrainerSpells(entry),
        trainer->TrainerTemplateId ? sObjectMgr.GetNpcTrainerTemplateSpells(trainer->TrainerTemplateId) : nullptr
    };
    for (TrainerSpellData const* list : lists)
        if (list)
            for (const auto& spell : list->spellList)
                if (LivingWowCanTrainSpell(bot, &spell.second))
                    return true;
    return false;
}
