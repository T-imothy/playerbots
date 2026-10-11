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
    class GeddonControlValue : public ManualSetValue<GeddonControl>
    {
    public:
        GeddonControlValue(PlayerbotAI* ai) : ManualSetValue<GeddonControl>(ai, GeddonControl(), "geddon control") {}
    };
}
