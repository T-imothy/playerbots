#pragma once
#include "playerbot/strategy/Value.h"
#include "EncounterPositionValue.h"
namespace ai
{
    struct GeddonControl
    {
        ObjectGuid boss, tank;
        encounter::Point tankPosition, rangedPosition;
    };
    class RagnarosControlValue : public ManualSetValue<GeddonControl>
    {
    public:
        RagnarosControlValue(PlayerbotAI* ai) : ManualSetValue<GeddonControl>(ai, GeddonControl(), "ragnaros control") {}
    };
    class GeddonControlValue : public ManualSetValue<GeddonControl>
    {
    public:
        GeddonControlValue(PlayerbotAI* ai) : ManualSetValue<GeddonControl>(ai, GeddonControl(), "geddon control") {}
    };
}
