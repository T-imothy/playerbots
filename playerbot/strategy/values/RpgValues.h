#pragma once
#include "playerbot/strategy/Value.h"

namespace ai
{
    class NextRpgActionValue : public ManualSetValue<std::string>
	{
	public:
        NextRpgActionValue(PlayerbotAI* ai, std::string defaultValue = "", std::string name = "next rpg action") : ManualSetValue(ai, defaultValue, name) {};
        void Set(std::string next) override;
        void Reset() override { Set(defaultValue); }
    };
}
