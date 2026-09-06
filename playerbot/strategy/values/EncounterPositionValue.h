#pragma once

#include "playerbot/strategy/Value.h"
#include "playerbot/strategy/EncounterGeometry.h"

namespace ai
{
    struct EncounterPosition
    {
        bool active = false;
        bool exclusive = true;
        uint32 map = 0, instance = 0;
        ObjectGuid boss, source;
        encounter::Point destination;
    };

    bool ValidateEncounterDestination(PlayerbotAI* ai, EncounterPosition& plan);
    float NativeEncounterSpellRadius(uint32 id, unsigned depth = 0);

    class MechanarPositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        MechanarPositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "mechanar position", 2) {}
        EncounterPosition Calculate() override;
    };

    class MoltenCorePositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        MoltenCorePositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "molten core position", 2) {}
        EncounterPosition Calculate() override;
    };

    class NetherspitePositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        NetherspitePositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "netherspite position", 2) {}
        EncounterPosition Calculate() override;
    };

    class OnyxiaPositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        OnyxiaPositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "onyxia position", 2) {}
        EncounterPosition Calculate() override;
        void Reset() override { CalculatedValue::Reset(); breath = 0; breathUntil = 0; }
    private:
        uint32 breath = 0;
        time_t breathUntil = 0;
    };
}
