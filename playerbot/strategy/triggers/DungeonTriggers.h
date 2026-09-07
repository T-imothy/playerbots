#pragma once
#include "playerbot/strategy/Trigger.h"

namespace ai
{
    class RotatingBeamTrigger : public Trigger
    {
    public:
        RotatingBeamTrigger(PlayerbotAI* ai) : Trigger(ai, "avoid rotating beam", 1) {}
        bool IsActive() override;
    };
    class VashjCoreTrigger : public Trigger
    {
    public:
        VashjCoreTrigger(PlayerbotAI* ai) : Trigger(ai, "vashj core relay", 1) {}
        bool IsActive() override;
    };
    class InnerDemonTrigger : public Trigger
    {
    public:
        InnerDemonTrigger(PlayerbotAI* ai) : Trigger(ai, "fight own inner demon", 1) {}
        bool IsActive() override;
    };
    class EadricRadianceTrigger : public Trigger
    {
    public:
        EadricRadianceTrigger(PlayerbotAI* ai) : Trigger(ai, "eadric face away", 1) {}
        bool IsActive() override;
    };
    class MoamManaControlTrigger : public Trigger
    {
    public:
        MoamManaControlTrigger(PlayerbotAI* ai) : Trigger(ai, "moam mana control", 1) {}
        bool IsActive() override;
    };
    class ViscidusFrostTrigger : public Trigger
    {
    public:
        ViscidusFrostTrigger(PlayerbotAI* ai) : Trigger(ai, "viscidus frost", 1) {}
        bool IsActive() override;
    };
    class HeiganDanceTrigger : public Trigger
    {
    public:
        HeiganDanceTrigger(PlayerbotAI* ai) : Trigger(ai, "heigan dance", 1) {}
        bool IsActive() override;
    };
    class NajentusSpineTrigger : public Trigger
    {
    public:
        NajentusSpineTrigger(PlayerbotAI* ai) : Trigger(ai, "najentus spine rescue", 1) {}
        bool IsActive() override;
    };
    class NajentusShieldTrigger : public Trigger
    {
    public:
        NajentusShieldTrigger(PlayerbotAI* ai) : Trigger(ai, "najentus break shield", 1) {}
        bool IsActive() override;
    };
    class ArchimondeTearsTrigger : public Trigger
    {
    public:
        ArchimondeTearsTrigger(PlayerbotAI* ai) : Trigger(ai, "archimonde tears", 1) {}
        bool IsActive() override;
    };
    class LinkedBurstTrigger : public Trigger
    {
    public:
        LinkedBurstTrigger(PlayerbotAI* ai) : Trigger(ai, "separate linked burst", 1) {}
        bool IsActive() override;
    };
    class AkilzonStormTrigger : public Trigger
    {
    public:
        AkilzonStormTrigger(PlayerbotAI* ai) : Trigger(ai, "akilzon storm shelter", 1) {}
        bool IsActive() override;
    };
    class ColdMovementTrigger : public Trigger
    {
    public:
        ColdMovementTrigger(PlayerbotAI* ai) : Trigger(ai, "move against cold", 1) {}
        bool IsActive() override;
    };
    class HakkarPoisonTrigger : public Trigger
    {
    public:
        HakkarPoisonTrigger(PlayerbotAI* ai) : Trigger(ai, "hakkar acquire poison", 1) {}
        bool IsActive() override;
    };
    class OssirianCrystalTrigger : public Trigger
    {
    public:
        OssirianCrystalTrigger(PlayerbotAI* ai) : Trigger(ai, "ossirian crystal", 1) {}
        bool IsActive() override;
    };
    class BossCoverTrigger : public Trigger
    {
    public:
        BossCoverTrigger(PlayerbotAI* ai) : Trigger(ai, "boss seek cover", 1) {}
        bool IsActive() override;
    };

    class DungeonAddTargetTrigger : public Trigger
    {
    public:
        DungeonAddTargetTrigger(PlayerbotAI* ai) : Trigger(ai, "dungeon priority add", 1) {}
        bool IsActive() override;
    };

    class SolarianPositionTrigger : public Trigger
    {
    public:
        SolarianPositionTrigger(PlayerbotAI* ai) : Trigger(ai, "solarian burst position", 1) {}
        bool IsActive() override;
    };

    class SolarianPriorityTargetTrigger : public Trigger
    {
    public:
        SolarianPriorityTargetTrigger(PlayerbotAI* ai) : Trigger(ai, "solarian priority target", 1) {}
        bool IsActive() override;
    };

    class MagtheridonCubeTrigger : public Trigger
    {
    public:
        MagtheridonCubeTrigger(PlayerbotAI* ai) : Trigger(ai, "magtheridon cube", 1) {}
        bool IsActive() override;
    };

    class GruulSpreadTrigger : public Trigger
    {
    public:
        GruulSpreadTrigger(PlayerbotAI* ai) : Trigger(ai, "gruul shatter spread", 1) {}
        bool IsActive() override;
    };

    class BossCastPositionTrigger : public Trigger
    {
    public:
        BossCastPositionTrigger(PlayerbotAI* ai) : Trigger(ai, "boss cast safe position", 1) {}
        bool IsActive() override;
    };

    class HostileGroundDamageTrigger : public Trigger
    {
    public:
        HostileGroundDamageTrigger(PlayerbotAI* ai) : Trigger(ai, "hostile ground damage", 1) {}
        bool IsActive() override;
    };

    class EnterDungeonTrigger : public Trigger
    {
    public:
        // You can get the mapID from worlddb > instance_template > map column
        // or from here https://wow.tools/dbc/?dbc=map&build=1.12.1.5875
        EnterDungeonTrigger(PlayerbotAI* ai, std::string name, std::string dungeonStrategy, uint32 mapID)
        : Trigger(ai, name, 5)
        , dungeonStrategy(dungeonStrategy)
        , mapID(mapID) {}

        bool IsActive() override;

    private:
        std::string dungeonStrategy;
        uint32 mapID;
    };

    class LeaveDungeonTrigger : public Trigger
    {
    public:
        // You can get the mapID from worlddb > instance_template > map column
        // or from here https://wow.tools/dbc/?dbc=map&build=1.12.1.5875
        LeaveDungeonTrigger(PlayerbotAI* ai, std::string name, std::string dungeonStrategy, uint32 mapID)
        : Trigger(ai, name, 5)
        , dungeonStrategy(dungeonStrategy)
        , mapID(mapID) {}

        bool IsActive() override;

    private:
        std::string dungeonStrategy;
        uint32 mapID;
    };

    class StartBossFightTrigger : public Trigger
    {
    public:
        StartBossFightTrigger(PlayerbotAI* ai, std::string name, std::string bossStrategy, uint64 bossID)
        : Trigger(ai, name, 1)
        , bossStrategy(bossStrategy)
        , bossID(bossID) {}

        bool IsActive() override;

    private:
        std::string bossStrategy;
        uint64 bossID;
    };

    class EndBossFightTrigger : public Trigger
    {
    public:
        EndBossFightTrigger(PlayerbotAI* ai, std::string name, std::string bossStrategy, uint64 bossID)
        : Trigger(ai, name, 5)
        , bossStrategy(bossStrategy)
        , bossID(bossID) {}

        bool IsActive() override;

    private:
        std::string bossStrategy;
        uint64 bossID;
    };

    class CloseToHazardTrigger : public Trigger
    {
    public:
        CloseToHazardTrigger(PlayerbotAI* ai, std::string name, int checkInterval, float hazardRadius, time_t hazardDuration)
        : Trigger(ai, name, checkInterval)
        , hazardRadius(hazardRadius)
        , hazardDuration(hazardDuration) {}

        bool IsActive() override final;

    protected:
        virtual std::list<ObjectGuid> GetPossibleHazards() = 0;
        virtual bool IsHazardValid(const ObjectGuid& hazzardGuid);

    private:
        float GetDistanceToHazard(const ObjectGuid& hazzardGuid);

    protected:
        float hazardRadius;
        time_t hazardDuration;
    };

    class CloseToGameObjectHazardTrigger : public CloseToHazardTrigger
    {
    public:
        CloseToGameObjectHazardTrigger(PlayerbotAI* ai, std::string name, uint32 gameObjectID, float radius, time_t expirationTime)
        : CloseToHazardTrigger(ai, name, 1, radius, expirationTime)
        , gameObjectID(gameObjectID) {}

    private:
        std::list<ObjectGuid> GetPossibleHazards() override;

    private:
        uint32 gameObjectID;
    };

    class CloseToCreatureHazardTrigger : public CloseToHazardTrigger
    {
    public:
        CloseToCreatureHazardTrigger(PlayerbotAI* ai, std::string name, uint32 creatureID, float radius, time_t expirationTime)
        : CloseToHazardTrigger(ai, name, 1, radius, expirationTime)
        , creatureID(creatureID) {}

    private:
        std::list<ObjectGuid> GetPossibleHazards() override;
        bool IsHazardValid(const ObjectGuid& hazzardGuid) override;

    protected:
        uint32 creatureID;
    };

    class CloseToHostileCreatureHazardTrigger : public CloseToCreatureHazardTrigger
    {
    public:
        CloseToHostileCreatureHazardTrigger(PlayerbotAI* ai, std::string name, uint32 creatureID, float radius, time_t expirationTime)
        : CloseToCreatureHazardTrigger(ai, name, creatureID, radius, expirationTime) {}

    private:
        std::list<ObjectGuid> GetPossibleHazards() override;
    };

    class CloseToCreatureTrigger : public Trigger
    {
    public:
        CloseToCreatureTrigger(PlayerbotAI* ai, std::string name, uint32 creatureID, float range, bool ignoreVictim = false, uint32 timeInterval = 1)
        : Trigger(ai, name, timeInterval)
        , creatureID(creatureID)
        , range(range)
        , ignoreVictim(ignoreVictim) {}

        bool IsActive() override;

    private:
        uint32 creatureID;
        float range;
        bool ignoreVictim;
    };

    class CloseToSpecificCreaturesTrigger : public Trigger
    {
    public:
        CloseToSpecificCreaturesTrigger(PlayerbotAI* ai, std::string name = "specific creature too close", float range = 10.0f, bool ignoreVictim = true)
        : Trigger(ai, name, 1)
        , range(range)
        , ignoreVictim(ignoreVictim) {}

        bool IsActive() override;

    private:
        float range;
        bool ignoreVictim;
    };

    class ItemReadyTrigger : public Trigger
    {
    public:
        ItemReadyTrigger(PlayerbotAI* ai, std::string name, uint32 itemID)
        : Trigger(ai, name, 1)
        , itemID(itemID) {}

        virtual bool IsActive() override;

    protected:
        uint32 itemID;
    };

    class ItemBuffReadyTrigger : public ItemReadyTrigger
    {
    public:
        ItemBuffReadyTrigger(PlayerbotAI* ai, std::string name, uint32 itemID, uint32 buffID)
        : ItemReadyTrigger(ai, name, itemID)
        , buffID(buffID) {}

        bool IsActive() override;

    private:
        uint32 buffID;
    };
}
