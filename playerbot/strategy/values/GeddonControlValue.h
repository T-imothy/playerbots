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
    struct MagmadarControl
    {
        ObjectGuid boss, tank;
        encounter::Point tankPosition;
        float facing = 0;
        time_t combatStart = 0;
    };
    class MagmadarControlValue : public ManualSetValue<MagmadarControl>
    {
    public:
        MagmadarControlValue(PlayerbotAI* ai) : ManualSetValue<MagmadarControl>(ai, MagmadarControl(), "magmadar control") {}
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
