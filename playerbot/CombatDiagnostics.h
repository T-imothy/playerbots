#pragma once
#include "Common.h"
#include <string>

class Unit;
class PlayerbotAI;
namespace ai
{
    class CombatActionContext
    {
    public:
        explicit CombatActionContext(const std::string& name);
        ~CombatActionContext();
        static std::string Current();
    private:
        const std::string* previous;
        bool enabled;
    };
    // Observation only. No spell checks, target selection or game state changes.
    class CombatDiagnostics
    {
    public:
        static bool Select(PlayerbotAI* ai);
        static void Record(PlayerbotAI* ai, const std::string& action, const std::string& source,
            const char* stage, int32 result, uint32 spell = 0, Unit* target = nullptr);
        static void Flush();
    };
}
