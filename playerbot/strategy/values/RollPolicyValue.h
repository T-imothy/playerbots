#pragma once
#include "playerbot/strategy/Value.h"

namespace ai
{
    // Independent of strategy presets: saving a loot preference must not also
    // save temporary combat strategies or depend on having a master at login.
    class RollPolicyValue : public ManualSetValue<std::string>
    {
    public:
        RollPolicyValue(PlayerbotAI* ai) : ManualSetValue(ai, "auto", "roll policy") {}
        static bool IsValid(const std::string& mode)
        { return mode == "auto" || mode == "pass" || mode == "greed" || mode == "need"; }
        std::string Get() override;
        std::string LazyGet() override { return Get(); }
        std::string Format() override { return Get(); }
        void Reset() override { loaded = false; value = "auto"; }
        bool Persist(const std::string& mode);
    private:
        bool loaded = false;
    };
}
