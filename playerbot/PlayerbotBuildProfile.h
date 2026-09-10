#pragma once

#include "Common.h"

#include <map>
#include <limits>
#include <string>
#include <vector>

class Item;
class Player;
struct ItemPrototype;

namespace ai
{
    enum class LivingBuildActivation : uint8
    {
        Main = 0,
        Offspec,
        PartyTemporary
    };

    struct LivingBotBuildProfile
    {
        uint32 characterGuid = 0;
        uint32 mainPathId = 0;
        uint32 offPathId = 0;
        uint32 activePathId = 0;
        uint32 partySessionId = 0;
        uint32 revision = 1;
        std::string mainSpecialization;
        std::string offSpecialization;
        std::string activeSpecialization;
        std::string mainArchetype;
        std::string offArchetype;
        std::string activeArchetype;
        std::string activeReason = "main";
        std::string gearProfile = "practical";
        uint8 gearAmbition = 50;
        uint8 performanceDrive = 50;
        uint8 roleFlexibility = 50;
        uint8 dungeonInterest = 50;
        uint8 raidAspiration = 50;
    };

    struct LivingGearScores
    {
        uint32 mainScore = 0;
        uint32 offScore = 0;
        uint32 activeScore = 0;
        uint32 sharedBonus = 0;
        uint32 effectiveScore = 0;
        uint8 armorPenaltyPercent = 0;
        bool preferredArmor = true;
        bool sharedUpgrade = false;
    };

    struct LivingGearDeficiency
    {
        uint8 slot = 0;
        uint32 itemEntry = 0;
        uint32 severity = 0;
        std::string reason;
    };

    class PlayerbotBuildProfileMgr
    {
    public:
        static PlayerbotBuildProfileMgr& instance();

        const LivingBotBuildProfile& Get(Player* bot);
        void Update(Player* bot);
        bool IsActive() const { return mode == "active"; }
        bool OffspecScoringEnabled() const { return IsActive() && offspecScoring; }
        bool OffspecLootEnabled() const { return IsActive() && offspecLoot; }
        bool ArmorPreferenceEnabled() const { return IsActive() && armorPreference; }
        bool GearingGoalsEnabled() const { return IsActive() && gearingGoals; }
        uint8 PreferredArmorReplacementPercent() const { return preferredArmorReplacementPercent; }
        bool ActivateTemporary(Player* bot, const std::string& specialization, uint32 partySessionId,
            const std::string& reason, std::string& outcome);
        bool ActivateTemporaryPath(Player* bot, uint32 pathId, uint32 partySessionId,
            const std::string& reason, std::string& outcome);
        bool SetMain(Player* bot, const std::string& specialization, std::string& outcome);
        bool SetOffspec(Player* bot, const std::string& specialization, std::string& outcome);
        bool ClearTemporary(Player* bot, uint32 partySessionId, std::string& outcome);

        std::string GetMainSpecialization(Player* bot);
        std::string GetOffSpecialization(Player* bot);
        std::string GetActiveSpecialization(Player* bot);
        std::string GetMainWeightName(Player* bot);
        std::string GetOffWeightName(Player* bot);
        std::string GetActiveWeightName(Player* bot);
        uint32 BestPathForRole(Player* bot, uint32 roleMask);
        std::string BestSpecializationForRole(Player* bot, uint32 roleMask);
        bool IsPathUsableForRole(Player* bot, uint32 pathId, uint32 roleMask = 0) const;
        LivingGearScores Evaluate(Player* bot, ItemPrototype const* proto);
        bool IsOffspecUpgrade(Player* bot, ItemPrototype const* proto, ItemPrototype const* comparison = NULL);
        bool CanCarryOffspecItem(Player* bot, ItemPrototype const* proto, bool acquiring = true);
        uint8 OffspecUpgradeThreshold(Player* bot);
        uint8 OffspecCarryLimit(Player* bot);
        std::vector<LivingGearDeficiency> GetGearingDeficiencies(Player* bot);
        bool HasGearingDeficiency(Player* bot);
        uint32 GearingGoalUtility(Player* bot);
        std::string DiagnosticsJson(Player* bot);

    private:
        PlayerbotBuildProfileMgr();
        void EnsureSchema();
        LivingBotBuildProfile Create(Player* bot);
        void Save(const LivingBotBuildProfile& profile);
        void LoadEquipment(uint32 characterGuid);
        void CaptureEquipment(Player* bot, const LivingBotBuildProfile& profile);
        void EquipSavedSet(Player* bot, const char* buildSlot);
        uint32 ChooseMainPath(Player* bot) const;
        uint32 ChooseOffPath(Player* bot, uint32 mainPathId, uint8 roleFlexibility) const;
        uint32 PathForSpecialization(Player* bot, const std::string& specialization,
            uint32 avoidPath = std::numeric_limits<uint32>::max()) const;
        uint32 PairScore(Player* bot, uint32 mainPathId, uint32 candidatePathId, uint8 roleFlexibility) const;
        uint32 EffectiveMainPath(Player* bot, const LivingBotBuildProfile& profile) const;
        void ReconcileAvailableBuild(Player* bot);
        static uint32 StableValue(uint32 guid, uint32 salt);
        static std::string GearProfileName(uint32 bucket);
        static uint8 PreferredArmorSubclass(Player* bot);
        static bool IsPhysicalOrTankWeight(const std::string& weightName);
        static std::string Escape(const std::string& value);

        bool schemaReady = false;
        std::string mode = "observe";
        bool persistentProfiles = true;
        bool temporaryPartyBuilds = true;
        bool offspecScoring = true;
        bool sharedItemBonuses = true;
        bool armorPreference = true;
        bool offspecLoot = true;
        bool gearingGoals = true;
        uint8 sharedUseBonusMaximumPercent = 15;
        uint8 physicalLowerArmorPenaltyPercent = 20;
        uint8 casterLowerArmorPenaltyPercent = 5;
        uint8 preferredArmorReplacementPercent = 85;
        uint8 minimumFreeBagSlots = 4;
        uint8 maximumOffspecBagUsagePercent = 80;
        time_t lastPolicyLoad = 0;
        std::map<uint32, LivingBotBuildProfile> profiles;
        std::map<uint32, time_t> nextSnapshot;
        std::map<uint32, time_t> nextAvailabilitySync;
        std::map<uint32, std::map<std::string, uint64> > equipmentSignatures;
        std::map<uint32, std::map<std::string, std::map<uint8, uint32> > > savedEquipment;
        std::map<uint32, std::map<std::string, std::map<uint8, uint32> > > savedEquipmentEntries;
    };
}

#define sPlayerbotBuildProfiles ai::PlayerbotBuildProfileMgr::instance()
