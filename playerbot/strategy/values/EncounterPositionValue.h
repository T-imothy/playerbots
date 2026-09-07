#pragma once

#include "playerbot/strategy/Value.h"
#include "playerbot/strategy/EncounterGeometry.h"
#include "playerbot/strategy/RotatingBeamGeometry.h"

class DynamicObject;

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
    bool ReadRotatingBeam(PlayerbotAI* ai, Unit* boss, EncounterPosition& plan, encounter::RotatingBeam& beam);
    bool ValidateRotatingBeamDestination(PlayerbotAI* ai, EncounterPosition& plan, const encounter::RotatingBeam& beam);
    class RotatingBeamPositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        RotatingBeamPositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "rotating beam position", 2) {}
        EncounterPosition Calculate() override;
    };
    float NativeEncounterSpellRadius(uint32 id, unsigned depth = 0);
    uint32 NativeBossEscapeSpell(uint32 map, uint32 entry, uint32 cast, bool regular = true);
    uint32 CurrentBossEscapeSpell(Player* bot, Unit* boss);
    const Spell* CurrentBossEscapeCast(Player* bot, Unit* boss);
    bool IsBossEscapeMap(uint32 map);
    bool AQWhirlwindThreats(PlayerbotAI* ai, EncounterPosition& plan, std::vector<encounter::Circle>& threats);
    bool IsLokenClosePhase(Player* bot, Unit* boss);
    bool PlanLokenClosePosition(PlayerbotAI* ai, Unit* boss, EncounterPosition& plan);
    uint32 BossCoverMechanic(PlayerbotAI* ai, Unit* boss, bool keepCover);
    bool IsBossCoverMap(uint32 map);
    bool IsBossCoverPosition(PlayerbotAI* ai, Unit* boss, const encounter::Point& point);
    bool LinkedBurstThreats(PlayerbotAI* ai, EncounterPosition& plan, std::vector<encounter::Circle>& threats);
    uint32 HeiganNextWave(Unit* controller);
    uint32 HeiganUpcomingWave(Unit* boss, Unit* controller);
    bool HeiganCloudSafe(Player* bot, Unit* boss, const encounter::Point& point);
    bool HeiganFloorThreats(PlayerbotAI* ai, const EncounterPosition& plan,
        std::vector<encounter::Circle>& threats, std::vector<encounter::Point>& safeFloor);
    class HeiganPositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        HeiganPositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "heigan dance position", 2) {}
        EncounterPosition Calculate() override;
    };
    Player* NajentusSpineVictim(PlayerbotAI* ai, GameObject* spine);
    Player* NajentusSpineUser(PlayerbotAI* ai, GameObject* spine);
    class NajentusPositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        NajentusPositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "najentus spine position", 2) {}
        EncounterPosition Calculate() override;
    };
    class LinkedBurstPositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        LinkedBurstPositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "linked burst position", 2) {}
        EncounterPosition Calculate() override;
    };
    Unit* AkilzonStormBoss(Player* bot, DynamicObject* eye);
    class AkilzonStormPositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        AkilzonStormPositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "akilzon storm position", 2) {}
        EncounterPosition Calculate() override;
    };
    bool IsOssirianCrystal(Player* bot, GameObject* crystal);
    bool IsHakkarPoisonSource(Player* bot, Unit* son);
    bool HasHakkarPoisonPreparation(Player* bot);
    class HakkarPositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        HakkarPositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "hakkar poison position", 2) {}
        EncounterPosition Calculate() override;
        void Reset() override { CalculatedValue::Reset(); preparationSon.Clear(); }
    private:
        ObjectGuid preparationSon;
        time_t preparationStarted = 0;
    };
    Unit* FindOssirianCrystalTrigger(Player* bot, GameObject* crystal);
    bool OssirianNeedsCrystal(Unit* boss);
    Player* OssirianCrystalUser(PlayerbotAI* ai, Unit* boss, GameObject* crystal);
    class OssirianPositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        OssirianPositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "ossirian crystal position", 2) {}
        EncounterPosition Calculate() override;
        void Reset() override { CalculatedValue::Reset(); anchorCrystal.Clear(); }
    private:
        ObjectGuid anchorCrystal;
        encounter::Point tankAnchor;
    };
    uint32 BurningAdrenalineAura(Unit* unit);
    bool BlackwingLairBurstThreats(PlayerbotAI* ai, EncounterPosition& plan,
        std::vector<encounter::Circle>& threats);
    uint32 NaxxramasBurstAura(Unit* unit);
    float NaxxramasBurstRadius(uint32 aura);
    bool NaxxramasBurstThreats(PlayerbotAI* ai, EncounterPosition& plan,
        std::vector<encounter::Circle>& threats);
    bool MoltenCoreThreats(PlayerbotAI* ai, EncounterPosition& plan,
        std::vector<encounter::Circle>& threats);
    bool MechanarThreats(PlayerbotAI* ai, EncounterPosition& plan,
        std::vector<encounter::Circle>& threats);
    bool GruulShatterThreats(PlayerbotAI* ai, EncounterPosition& plan,
        std::vector<encounter::Circle>& threats);
    float SolarianBurstRadius();
    bool SolarianBurstThreats(PlayerbotAI* ai, EncounterPosition& plan,
        std::vector<encounter::Circle>& threats);

    class SolarianPositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        SolarianPositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "solarian burst position", 2) {}
        EncounterPosition Calculate() override;
    };

    bool HasMagtheridonChannel(Player* player);
    bool IsMagtheridonNova(Unit* boss);
    bool IsMagtheridonCubeUser(PlayerbotAI* ai, Player* player, Unit* boss);
    bool IsMagtheridonCube(Player* player, GameObject* cube);
    Unit* FindMagtheridonCubeTrigger(Player* player, GameObject* cube);

    class MagtheridonPositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        // CalculatedValue's legacy interval is halved; 2 caches for one second.
        MagtheridonPositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "magtheridon cube position", 2) {}
        EncounterPosition Calculate() override;
    };

    class GruulPositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        GruulPositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "gruul spread position", 2) {}
        EncounterPosition Calculate() override;
    };

    class NaxxramasPositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        NaxxramasPositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "naxxramas position", 2) {}
        EncounterPosition Calculate() override;
    };

    class BlackwingLairPositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        BlackwingLairPositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "blackwing lair position", 2) {}
        EncounterPosition Calculate() override;
    };

    class BossCastPositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        BossCastPositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "boss cast position", 2) {}
        EncounterPosition Calculate() override;
    };

    class BossCoverPositionValue : public CalculatedValue<EncounterPosition>
    {
    public:
        BossCoverPositionValue(PlayerbotAI* ai) : CalculatedValue(ai, "boss cover position", 2) {}
        EncounterPosition Calculate() override;
        void Reset() override { CalculatedValue::Reset(); shelterBoss.Clear(); }
    private:
        ObjectGuid shelterBoss;
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
