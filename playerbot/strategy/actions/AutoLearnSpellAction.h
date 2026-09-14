#pragma once


#include "playerbot/playerbot.h"
#include "playerbot/strategy/Action.h"

namespace ai
{
    class AutoLearnSpellAction : public Action {
    public:
        AutoLearnSpellAction(PlayerbotAI* ai, std::string name = "auto learn spell") : Action(ai, name) {}
        
    public:
        virtual bool Execute(Event& event) override;
        virtual bool isUsefulWhenStunned() override { return true; }
        // Login/randomization must not rescan quests or broadcast a level-up.
        void CatchUpTrainerSpells(std::ostringstream* out = nullptr);
        void LearnClassLevelSpells(bool includeHighLevelQuestRewards = false);

    private: 
        void LearnSpells(std::ostringstream* out);
        bool LearnTrainerSpells(std::ostringstream* out, std::vector<uint32> const& entries, bool classOnly = false);
        void LearnQuestSpells(std::ostringstream* out);
        void LearnDroppedSpells(std::ostringstream* out);
        void GetClassQuestItem(Quest const* quest, std::ostringstream* out);
        bool LearnSpell(uint32 spellId, std::ostringstream* out);
        bool LearnSpellFromSpell(uint32 spellId, std::ostringstream* out);
        bool IsValidSpell(uint32 spellId);
        bool IsTeachingSpellListedAsSpell(uint32 spellId);
    };
}
