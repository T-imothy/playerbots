#pragma once

#include "playerbot/strategy/Value.h"
#include "playerbot/strategy/EncounterGeometry.h"

namespace ai
{
    struct EncounterPosition
    {
        bool active = false;
        bool exclusive = true;
        uint32 map = 0, instance = 0, spell = 0;
        ObjectGuid boss, source;
        encounter::Point destination;
    };

    bool ValidateEncounterDestination(PlayerbotAI* ai, EncounterPosition& plan);
    float NativeEncounterSpellRadius(uint32 id, unsigned depth = 0);
    uint32 NativeBossEscapeSpell(uint32 map, uint32 entry, uint32 cast);
    bool IsBossEscapeMap(uint32 map);

    class BossCastPositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        BossCastPositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "boss cast position", 1) {}
        EncounterPosition Calculate() override;
    };

    class AranFlameWreathValue : public BoolCalculatedValue
    {
    public:
        AranFlameWreathValue(PlayerbotAI* ai) : BoolCalculatedValue(ai, "aran flame wreath", 1) {}
        bool Calculate() override;
    };

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
