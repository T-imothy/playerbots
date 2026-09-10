#pragma once

#include "Common.h"
#include "Globals/SharedDefines.h"
#include "Entities/ObjectGuid.h"

#include <map>
#include <set>
#include <string>
#include <vector>

class Group;
class GroupLootRoll;
class Player;
class Unit;

namespace ai
{
    class Action;
    enum class ItemUsage : uint8;

    enum class LivingPartyRole : uint8
    {
        Auto = 0,
        Tank,
        Healer,
        Damage
    };

    enum class LivingPartyPhase : uint8
    {
        Idle = 0,
        Armed,
        Pulling,
        Stabilizing,
        Engaged,
        Recovering
    };

    struct LivingPartyRoleState
    {
        LivingPartyRole primary = LivingPartyRole::Auto;
        LivingPartyRole secondary = LivingPartyRole::Auto;
        std::string source = "default";
        bool locked = false;
    };

    struct LivingPartyCombatPolicy
    {
        std::string mode = "observe";
        bool engagementGating = true;
        bool threatThrottling = true;
        bool healerDuty = true;
        bool tacticalRules = true;
        bool addonTelemetry = true;
        bool manaAssistance = true;
        bool humanFirstLoot = true;
        bool equipmentLootNeed = true;
        bool professionLootNeed = true;
        bool questLootNeed = true;
        bool announceLootNeed = true;
        bool botLedAutoMark = true;
        bool humanLedAutoMark = false;
        uint32 stabilizeMilliseconds = 2000;
        uint32 maximumHoldMilliseconds = 6000;
        uint32 ruleArmSeconds = 600;
        uint8 softThreatPercent = 60;
        uint8 hardThreatPercent = 80;
        uint8 resumeThreatPercent = 55;
        uint8 emergencyHealthPercent = 35;
        uint8 tankHealPercent = 70;
        uint8 partyHealPercent = 60;
        uint8 hotHealthPercent = 85;
        uint8 manaReservePercent = 30;
        uint8 maximumOverhealPercent = 40;
        uint16 combatManaRegenPercent = 125;
        uint16 combatCastingRegenFloorPercent = 25;
        uint16 outOfCombatManaRegenPercent = 200;
        uint8 humanRollSafetySeconds = 3;
        uint32 telemetryMilliseconds = 500;
    };

    struct LivingPartyTacticalRule
    {
        uint32 id = 0;
        std::string selectorType;
        uint32 selectorId = 0;
        std::string treatment;
        ObjectGuid assignee;
        time_t createdAt = 0;
        time_t expiresAt = 0;
        bool activated = false;
    };

    class PlayerbotPartyCombatCoordinator
    {
    public:
        static PlayerbotPartyCombatCoordinator& instance();

        void Update(Player* bot);
        bool HandleAddonMessage(Player* receiverBot, Player* sender, const std::string& message);
        bool CanInitiate(Player* bot, Unit* target) const;
        float ActionMultiplier(Player* bot, Action* action) const;
        float AdjustManaRegen(Player* member, bool recentCast, float currentRegen, float normalRegen) const;
        bool ShouldDeferLootRoll(Player* bot, GroupLootRoll* roll) const;
        bool HumanNeededLoot(Player* bot, GroupLootRoll* roll) const;
        bool BotCanNeedForUsage(ItemUsage usage) const;
        bool ShouldAnnounceLootNeed() const;
        bool IsActiveMixedParty(Player* member) const;
        LivingPartyRoleState GetRole(Player* member) const;
        Unit* GetPreferredTarget(Player* bot) const;
        std::string GetCandidateJson(Player* bot, Player* speaker) const;
        bool SupportsProposal(const std::string& type) const;
        std::string ExecuteProposal(Player* bot, Player* requester, const std::string& type,
            const std::string& capabilityRef, const std::string& intent);
        const LivingPartyCombatPolicy& GetPolicy() const { return policy; }

        static const char* RoleName(LivingPartyRole role);
        static const char* PhaseName(LivingPartyPhase phase);

    private:
        struct GroupState
        {
            uint32 groupId = 0;
            uint32 revision = 0;
            LivingPartyPhase phase = LivingPartyPhase::Idle;
            ObjectGuid tank;
            ObjectGuid healer;
            ObjectGuid puller;
            ObjectGuid primaryTarget;
            ObjectGuid secondaryTarget;
            std::map<ObjectGuid, LivingPartyRoleState> roles;
            std::map<ObjectGuid, LivingPartyRole> overrides;
            std::set<ObjectGuid> addonClients;
            std::set<ObjectGuid> threatClients;
            std::set<ObjectGuid> approvedTargets;
            std::set<ObjectGuid> threatHeld;
            std::set<ObjectGuid> threatSoftHeld;
            std::vector<LivingPartyTacticalRule> rules;
            bool hold = false;
            bool humanLeader = false;
            uint32 phaseSince = 0;
            uint32 tankControlSince = 0;
            uint32 lastTelemetry = 0;
            uint32 lastRoleSignature = 0;
            uint32 lastSeen = 0;
            uint32 lastCombatSeen = 0;
        };

        PlayerbotPartyCombatCoordinator();
        void ReloadPolicy() const;
        GroupState* EnsureState(Player* member) const;
        void RefreshRoles(Group* group, GroupState& state) const;
        void RefreshCombat(Group* group, GroupState& state) const;
        void RefreshMarkers(Group* group, GroupState& state) const;
        void SendSnapshot(Group* group, GroupState& state) const;
        void SendAddon(Player* source, Player* target, const std::string& payload) const;
        LivingPartyRoleState InferRole(Player* member, const GroupState& state) const;
        bool HasShield(Player* member) const;
        bool HasHealingSpell(Player* member) const;
        Player* FindMember(Group* group, const std::string& name) const;
        Player* FindMember(Group* group, ObjectGuid guid) const;
        bool IsMixedGroup(Group* group) const;
        bool IsLeader(Player* player) const;
        bool IsApprovedTarget(const GroupState& state, Unit* target) const;
        uint8 ThreatPercent(Player* member, Unit* target, Player* tank) const;
        static std::vector<std::string> Fields(const std::string& message);
        static std::string Escape(const std::string& value);

        mutable LivingPartyCombatPolicy policy;
        mutable std::map<uint32, GroupState> groups;
        mutable time_t lastPolicyLoad = 0;
        mutable time_t lastCleanup = 0;
        mutable uint32 nextRuleId = 1;
    };
}

#define sPlayerbotPartyCombatCoordinator ai::PlayerbotPartyCombatCoordinator::instance()
